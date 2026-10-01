import io
import logging
from PIL import Image
import pypdf

logger = logging.getLogger(__name__)

_rec_predictor = None


def load_models():
    global _rec_predictor
    logger.info("Ładowanie modeli Surya OCR...")
    from surya.recognition import RecognitionPredictor
    _rec_predictor = RecognitionPredictor()
    logger.info("Modele OCR załadowane.")


def _ensure_models():
    if _rec_predictor is None:
        load_models()


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
            ['pdftotext', '-layout', '-', '-'],
            input=data, capture_output=True, timeout=15,
        )
        if result.returncode == 0:
            text = result.stdout.decode('utf-8', errors='replace').strip()
            if len(text) >= 200:
                return text
    except Exception:
        pass
    return None


def run_ocr_on_bytes(data: bytes, content_type: str) -> str:
    if 'pdf' in content_type:
        text = _try_pdftotext(data)
        if text:
            return text
    _ensure_models()
    images = _load_image(data, content_type)
    all_text = []
    for image in images[:4]:
        results = _rec_predictor([image])
        if results and results[0].text_lines:
            lines = sorted(results[0].text_lines, key=lambda ln: (ln.bbox[1], ln.bbox[0]))
            all_text.append('\n'.join(ln.text for ln in lines if ln.text.strip()))
    return "\n\n".join(all_text)
