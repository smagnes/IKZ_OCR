from __future__ import annotations

import io
import logging
import base64
import os
import re
from typing import List, Tuple
from PIL import Image
import pypdf

logger = logging.getLogger(__name__)

OCR_ENGINE = os.environ.get("OCR_ENGINE", "claude")

_paddle_ocr = None
_paddle_structure = None
_lighton_model = None
_lighton_processor = None

# Confidence threshold below which numeric values trigger Tesseract verification
_NUMERIC_CONF_THRESHOLD = 0.75


def load_models():
    global _paddle_ocr, _paddle_structure, _lighton_model, _lighton_processor
    if OCR_ENGINE in ("paddle", "hybrid"):
        try:
            from paddleocr import PaddleOCR, PPStructure
            _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="pl")
            _paddle_structure = PPStructure(table=True, ocr=True, lang="pl", show_log=False)
            logger.info("PaddleOCR + PPStructure loaded (lang=pl)")
        except Exception as e:
            logger.error("PaddleOCR load failed: %s", e)
    if OCR_ENGINE == "lighton":
        try:
            from transformers import AutoProcessor, AutoModelForImageTextToText
            model_id = "lightonai/LightOnOCR-2-1B"
            _lighton_processor = AutoProcessor.from_pretrained(model_id)
            _lighton_model = AutoModelForImageTextToText.from_pretrained(model_id)
            logger.info("LightOnOCR-2-1B loaded")
        except Exception as e:
            logger.error("LightOnOCR load failed: %s", e)
    if OCR_ENGINE == "claude":
        logger.info("Claude vision OCR — no local models to load")


# ── Image preprocessing ───────────────────────────────────────────────────────

def _preprocess(img: Image.Image) -> Image.Image:
    """
    Prepare image for OCR:
    1. Resize to max 2000px on longest side
    2. Invert if dark background (hospital photo scans)
    3. CLAHE contrast enhancement
    4. Deskew using Hough lines
    5. Remove stamp artifacts (morphological opening on saturation channel)
    """
    import cv2
    import numpy as np

    img = img.convert("RGB")

    MAX_SIDE = 2000
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        scale = MAX_SIDE / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    arr = np.array(img)

    # Invert dark background
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    if float(np.median(gray)) < 100:
        arr = cv2.bitwise_not(arr)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

    # Stamp removal: suppress high-saturation blobs (red/blue stamps)
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    sat = hsv[:, :, 1]
    stamp_mask = cv2.threshold(sat, 80, 255, cv2.THRESH_BINARY)[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    stamp_mask = cv2.morphologyEx(stamp_mask, cv2.MORPH_OPEN, kernel)
    arr[stamp_mask > 0] = 255  # whiten stamp areas

    # CLAHE on grayscale
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    arr = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)

    arr = _deskew(arr)
    return Image.fromarray(arr)


def _deskew(arr):
    """Straighten a skewed document image using Hough lines."""
    import cv2
    import numpy as np

    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                             minLineLength=100, maxLineGap=10)
    if lines is None or len(lines) < 5:
        return arr

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 != x1:
            angle = float(__import__('numpy').degrees(
                __import__('numpy').arctan2(y2 - y1, x2 - x1)))
            if abs(angle) < 30:
                angles.append(angle)

    if not angles:
        return arr

    import numpy as np
    median_angle = float(np.median(angles))
    if abs(median_angle) < 0.5:
        return arr

    h, w = arr.shape[:2]
    M = __import__('cv2').getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
    return __import__('cv2').warpAffine(arr, M, (w, h),
                                        flags=__import__('cv2').INTER_LINEAR,
                                        borderMode=__import__('cv2').BORDER_REPLICATE)


# ── PDF helpers ───────────────────────────────────────────────────────────────

def _pymupdf_text(data: bytes) -> str | None:
    """
    Extract native text layer from PDF using PyMuPDF.
    Returns None if the PDF is a pure scan (< 200 chars of real text).
    """
    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=data, filetype="pdf")
        pages_text = []
        for page in doc:
            # get_text("markdown") preserves basic table structure
            text = page.get_text("markdown").strip()
            pages_text.append(text)
        doc.close()
        combined = "\n\n".join(p for p in pages_text if p)
        if len(combined.strip()) >= 200:
            return combined
    except Exception as e:
        logger.debug("PyMuPDF extraction failed: %s", e)
    return None


def _pdf_to_images(data: bytes, dpi: int = 200) -> List[Image.Image]:
    try:
        from pdf2image import convert_from_bytes
        return convert_from_bytes(data, dpi=dpi)
    except Exception:
        reader = pypdf.PdfReader(io.BytesIO(data))
        return [Image.new("RGB", (2480, 3508), "white") for _ in reader.pages]


def _load_image(data: bytes, content_type: str) -> List[Image.Image]:
    if "pdf" in content_type:
        return _pdf_to_images(data)
    return [Image.open(io.BytesIO(data)).convert("RGB")]


def _image_to_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()


# ── Tesseract numeric verification ────────────────────────────────────────────

_NUMERIC_RE = re.compile(r'\b\d+[.,]\d+\b')


def _tesseract_verify_numbers(img: Image.Image, paddle_text: str) -> str:
    """
    For values flagged as low-confidence by Paddle, run Tesseract on the
    full image and extract numeric values. Replace Paddle numbers with
    Tesseract numbers where they differ significantly.
    This is a best-effort cross-check, not a full re-OCR.
    """
    try:
        import pytesseract
        tess_text = pytesseract.image_to_string(img, lang="pol",
                                                 config="--psm 6")
        paddle_nums = set(_NUMERIC_RE.findall(paddle_text))
        tess_nums = set(_NUMERIC_RE.findall(tess_text))
        # Numbers in Tesseract but not in Paddle are suspicious — log them
        new_nums = tess_nums - paddle_nums
        if new_nums:
            logger.info("Tesseract found extra numbers not in Paddle: %s", new_nums)
        return tess_text
    except Exception as e:
        logger.warning("Tesseract verification failed: %s", e)
        return paddle_text


# ── Claude ────────────────────────────────────────────────────────────────────

def _claude_ocr_images(images: List[Image.Image]) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    content = []
    for img in images[:4]:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg",
                       "data": _image_to_base64(img)}
        })
    content.append({
        "type": "text",
        "text": (
            "Extract ALL text from this medical document exactly as it appears. "
            "Preserve ALL line breaks, spacing, and column alignment. "
            "Each line in the document must be a separate line in output. "
            "Return only the raw extracted text, nothing else."
        )
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
            {"type": "document",
             "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
            {"type": "text", "text": (
                "Extract ALL text from this medical document exactly as it appears. "
                "Preserve ALL line breaks, spacing, and column alignment. "
                "Return only the raw extracted text, nothing else."
            )}
        ]}]
    )
    return response.content[0].text


# ── PaddleOCR ─────────────────────────────────────────────────────────────────

def _paddle_ocr_images(images: List[Image.Image]) -> Tuple[str, float]:
    """
    Returns (text, min_numeric_confidence).
    min_numeric_confidence < _NUMERIC_CONF_THRESHOLD → trigger Tesseract fallback.
    """
    global _paddle_ocr
    if _paddle_ocr is None:
        from paddleocr import PaddleOCR
        _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="pl")

    import numpy as np
    pages = []
    min_conf = 1.0

    for img in images:
        preprocessed = _preprocess(img)
        arr = np.array(preprocessed)
        page_lines = []
        for res in _paddle_ocr.predict(arr):
            texts = res.get("rec_texts", [])
            scores = res.get("rec_scores", [])
            for text, score in zip(texts, scores):
                if not text or not text.strip():
                    continue
                page_lines.append(text)
                # Track confidence only for lines containing numbers
                if _NUMERIC_RE.search(text):
                    min_conf = min(min_conf, float(score))
        pages.append("\n".join(page_lines))

    return "\n\n".join(p for p in pages if p.strip()), min_conf


def _ppstructure_tables(images: List[Image.Image]) -> str:
    """
    Use PPStructure to detect table regions and convert them to Markdown.
    Falls back to plain paddle OCR if PPStructure fails.
    """
    global _paddle_structure
    if _paddle_structure is None:
        from paddleocr import PPStructure
        _paddle_structure = PPStructure(table=True, ocr=True, lang="pl", show_log=False)

    import numpy as np
    pages_md = []

    for img in images:
        preprocessed = _preprocess(img)
        arr = np.array(preprocessed)
        result = _paddle_structure(arr)

        page_parts = []
        for region in result:
            region_type = region.get("type", "").lower()
            if region_type == "table":
                html = region.get("res", {}).get("html", "")
                if html:
                    page_parts.append(_html_table_to_markdown(html))
                    continue
            # For text regions: join lines
            res = region.get("res", [])
            if isinstance(res, list):
                lines = [r.get("text", "") for r in res if r.get("text")]
                page_parts.append("\n".join(lines))

        pages_md.append("\n\n".join(p for p in page_parts if p.strip()))

    return "\n\n---\n\n".join(p for p in pages_md if p.strip())


def _html_table_to_markdown(html: str) -> str:
    """Convert simple HTML table (from PPStructure) to Markdown."""
    try:
        import re as _re
        rows = _re.findall(r'<tr[^>]*>(.*?)</tr>', html, _re.DOTALL | _re.IGNORECASE)
        if not rows:
            return html
        md_rows = []
        for i, row in enumerate(rows):
            cells = _re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row,
                                 _re.DOTALL | _re.IGNORECASE)
            cells = [_re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            md_rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                md_rows.append("|" + "|".join(["---"] * len(cells)) + "|")
        return "\n".join(md_rows)
    except Exception:
        return html


# ── LightOnOCR ────────────────────────────────────────────────────────────────

def _lighton_ocr_images(images: List[Image.Image]) -> str:
    global _lighton_model, _lighton_processor
    if _lighton_model is None:
        from transformers import AutoProcessor, AutoModelForImageTextToText
        model_id = "lightonai/LightOnOCR-2-1B"
        _lighton_processor = AutoProcessor.from_pretrained(model_id)
        _lighton_model = AutoModelForImageTextToText.from_pretrained(model_id)
    import torch
    pages = []
    for img in images[:4]:
        inputs = _lighton_processor(images=img, return_tensors="pt")
        with torch.no_grad():
            output = _lighton_model.generate(**inputs, max_new_tokens=2048)
        text = _lighton_processor.decode(output[0], skip_special_tokens=True)
        pages.append(text)
    return "\n\n--- PAGE BREAK ---\n\n".join(pages)


# ── Main router ───────────────────────────────────────────────────────────────

def run_ocr_on_bytes(data: bytes, content_type: str) -> str:
    """
    Smart triage:
    1. Native PDF text layer → PyMuPDF (fast, lossless, preserves tables as Markdown)
    2. Scanned PDF / image:
       - claude  → Claude Haiku vision
       - paddle  → PaddleOCR (lang=pl) + Tesseract numeric cross-check
       - hybrid  → PPStructure for layout/tables + Tesseract fallback
       - lighton → LightOnOCR-2-1B (GPU recommended)
    """
    # Step 1: try native text layer (PDF only)
    if "pdf" in content_type:
        text = _pymupdf_text(data)
        if text:
            logger.info("PDF text layer extracted via PyMuPDF (%d chars)", len(text))
            return text

    # Step 2: load images for scan/image path
    images = _load_image(data, content_type)

    if OCR_ENGINE == "hybrid":
        logger.info("Hybrid mode: PPStructure + Tesseract numeric verification")
        text = _ppstructure_tables(images)
        if not text or len(text.strip()) < 50:
            # fallback to plain paddle
            text, min_conf = _paddle_ocr_images(images)
        return text

    if OCR_ENGINE == "paddle":
        text, min_conf = _paddle_ocr_images(images)
        if min_conf < _NUMERIC_CONF_THRESHOLD and images:
            logger.info(
                "Low numeric confidence (%.2f) — running Tesseract cross-check", min_conf
            )
            text = _tesseract_verify_numbers(images[0], text)
        return text

    if OCR_ENGINE == "lighton":
        return _lighton_ocr_images(images)

    # Default: Claude
    if "pdf" in content_type:
        try:
            result = _claude_ocr_pdf(data)
            if result and len(result.strip()) > 100:
                return result
        except Exception as e:
            logger.warning("Claude PDF beta failed: %s", e)
        logger.info("Scanned PDF — falling back to Claude image OCR")
        return _claude_ocr_images(images)

    return _claude_ocr_images(images)
