import io
import logging
import base64
import os
from PIL import Image
import pypdf

logger = logging.getLogger(__name__)

_rec_predictor = None


def load_models():
    logger.info("Claude vision OCR - no models to load")


def _pdf_to_images(data: bytes) -> list[Image.Image]:
    try:
        from pdf2image import convert_from_bytes
        return convert_from_bytes(data, dpi=200)
    except Exception:
        reader = pypdf.PdfReader(io.BytesIO(data))
        return [Image.new("RGB", (2480, 3508), "white") for _ in reader.pages]


def _load_image(data: bytes, content_type: str) -> list[Image.Image]:
    if "pdf" in content_type:
        return _pdf_to_images(data)
    return [Image.open(io.BytesIO(data)).convert("RGB")]


def _try_pdftotext(data: bytes) -> str | None:
    import subprocess
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-", "-"],
            input=data, capture_output=True, timeout=15,
        )
        if result.returncode == 0:
            text = result.stdout.decode("utf-8", errors="replace").strip()
            if len(text) >= 200:
                return text
    except Exception:
        pass
    return None


def _image_to_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()


def _claude_ocr_images(images: list[Image.Image]) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    content = []
    for img in images[:4]:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": _image_to_base64(img)}
        })
    content.append({
        "type": "text",
        "text": "Extract ALL text from this medical document exactly as it appears. Preserve ALL line breaks, spacing, and column alignment. Each line in the document must be a separate line in output. Return only the raw extracted text, nothing else."
    })
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{"role": "user", "content": content}]
    )
    return response.content[0].text


def _claude_ocr_pdf(data: bytes) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    b64 = base64.b64encode(data).decode()
    response = client.beta.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        betas=["pdfs-2024-09-25"],
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
            {"type": "text", "text": "Extract ALL text from this medical document exactly as it appears. Preserve ALL line breaks, spacing, and column alignment. Each line in the document must be a separate line in output. Return only the raw extracted text, nothing else."}
        ]}]
    )
    return response.content[0].text


def run_ocr_on_bytes(data: bytes, content_type: str) -> str:
    if "pdf" in content_type:
        text = _try_pdftotext(data)
        if text:
            return text
        try:
            result = _claude_ocr_pdf(data)
            if result and len(result.strip()) > 100:
                return result
        except Exception as e:
            logger.warning("Claude PDF beta failed: %s", e)
        logger.info("Scanned PDF detected, using image OCR fallback")
        images = _pdf_to_images(data)
        return _claude_ocr_images(images)
    else:
        images = _load_image(data, content_type)
        return _claude_ocr_images(images)

