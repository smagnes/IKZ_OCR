"""
Lokalny tłumacz PL→EN — Helsinki-NLP/opus-mt-pl-en (MarianMT, ~300MB, CPU).
Zero danych na zewnątrz. Lazy-load przy pierwszym użyciu.
"""
from __future__ import annotations
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_tokenizer = None
_model = None

MODEL_ID = "Helsinki-NLP/opus-mt-pl-en"
MAX_CHUNK_CHARS = 400   # MarianMT handles ~512 tokens; 400 chars ≈ safe limit


def _load() -> None:
    global _tokenizer, _model
    if _model is not None:
        return
    logger.info("Loading Helsinki-NLP/opus-mt-pl-en…")
    from transformers import MarianMTModel, MarianTokenizer
    _tokenizer = MarianTokenizer.from_pretrained(MODEL_ID)
    _model = MarianMTModel.from_pretrained(MODEL_ID)
    logger.info("Translation model ready")


def _split_to_chunks(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """Split on sentences; accumulate until chunk would exceed max_chars."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks: List[str] = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = sent
        else:
            current = (current + " " + sent).strip() if current else sent
    if current:
        chunks.append(current.strip())
    return chunks


def translate_pl_en(text: str) -> str:
    """Translate Polish text to English locally. Returns the translated string."""
    if not text or not text.strip():
        return text
    _load()
    chunks = _split_to_chunks(text)
    translated_parts: List[str] = []
    for chunk in chunks:
        inputs = _tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512)
        import torch
        with torch.no_grad():
            output = _model.generate(**inputs, max_new_tokens=512)
        translated = _tokenizer.decode(output[0], skip_special_tokens=True)
        translated_parts.append(translated)
    return " ".join(translated_parts)


def is_model_loaded() -> bool:
    return _model is not None
