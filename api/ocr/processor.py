import io
import logging
from PIL import Image
import pypdf

logger = logging.getLogger(__name__)

_det_predictor = None
_rec_predictor = None


def load_models():
    global _det_predictor, _rec_predictor
    logger.info("Ładowanie modeli Surya OCR 0.13...")
    from surya.models import DetectionPredictor, RecognitionPredictor
    _det_predictor = DetectionPredictor()
    _rec_predictor = RecognitionPredictor()
    logger.info("Modele OCR załadowane.")


def _ensure_models():
    if _det_predictor is None:
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
    """Fast-path for digital PDFs: pdftotext is faster and more accurate than Surya OCR.
    Returns None if not available or file is scanned (text < 200 chars)."""
    import subprocess
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', '-', '-'],
            input=data,
            capture_output=True,
            timeout=15,
        )
        if result.returncode == 0:
            text = result.stdout.decode('utf-8', errors='replace').strip()
            if len(text) >= 200:
                return text
    except Exception:
        pass
    return None


def _reconstruct_layout(text_lines, img_w: int, img_h: int) -> str:
    """Sort Surya text_lines by bounding-box position to produce reading-order text.

    Surya reads each detected text region independently and returns them in an order
    that reflects its internal detection logic — often column-by-column (rightmost first)
    rather than row-by-row. This function restores the correct visual reading order:
    top→bottom, left→right within each row.
    """
    lines = [ln for ln in text_lines if ln.text.strip()]
    if not lines:
        return ""

    # 1 % of image height as the row-grouping tolerance
    row_tol = max(8, img_h * 0.010)
    # Scale factor: how many image-pixels per output space character
    px_per_sp = max(1.0, img_w / 110.0)

    # Sort by top-Y of bounding box, breaking ties by left-X
    sorted_lines = sorted(lines, key=lambda ln: (ln.bbox[1], ln.bbox[0]))

    # Group into visual rows
    rows: list[list] = []
    cur_row = [sorted_lines[0]]
    cur_y = sorted_lines[0].bbox[1]

    for ln in sorted_lines[1:]:
        if ln.bbox[1] - cur_y <= row_tol:
            cur_row.append(ln)
        else:
            rows.append(cur_row)
            cur_row = [ln]
            cur_y = ln.bbox[1]
    if cur_row:
        rows.append(cur_row)

    # Within each row: sort L→R, insert spaces proportional to visual gap
    out: list[str] = []
    for row in rows:
        row = sorted(row, key=lambda ln: ln.bbox[0])
        parts: list[str] = []
        prev_x2: float = 0.0
        for ln in row:
            x1, _, x2, _ = ln.bbox
            if parts:
                gap = max(1, round((x1 - prev_x2) / px_per_sp))
                parts.append(' ' * gap)
            parts.append(ln.text)
            prev_x2 = x2
        out.append(''.join(parts))

    return '\n'.join(out)


def run_ocr_on_bytes(data: bytes, content_type: str) -> str:
    # Digital PDFs: use pdftotext (faster, no column scrambling)
    if 'pdf' in content_type:
        text = _try_pdftotext(data)
        if text:
            return text

    _ensure_models()

    images = _load_image(data, content_type)
    all_text = []

    for image in images[:4]:
        results = _rec_predictor(
            images=[image],
            langs=[["pl", "en"]],
            det_predictor=_det_predictor,
        )
        if results and results[0].text_lines:
            text = _reconstruct_layout(
                results[0].text_lines, image.width, image.height
            )
            all_text.append(text)

    return "\n\n".join(all_text)
