from __future__ import annotations
import re

# ── PII patterns ───────────────────────────────────────────────────────────────

# PESEL on one line (11 digits, not preceded/followed by digit)
_PESEL = re.compile(r'(?<!\d)\d{11}(?!\d)')

# PESEL split across line break: e.g. "720831\n12345"
_PESEL_SPLIT = re.compile(r'(?<!\d)(\d{6})\n(\d{5})(?!\d)')

_NIP = re.compile(r'\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b')

# Birth date only after explicit keyword context
_DATE_BIRTH = re.compile(
    r'(ur\.?\s*:?\s*|data\s+ur[oó]dze\w*\s*:?\s*|date\s+of\s+birth\s*:?\s*)'
    r'((?:19|20)\d{2}[-./]\d{2}[-./]\d{2})',
    re.IGNORECASE
)

_PHONE = re.compile(r'(\+48[\s-]?)?\b\d{3}[\s-]?\d{3}[\s-]?\d{3}\b')

_EMAIL = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')

_STREET = re.compile(
    r'\b(ul\.|al\.|pl\.|os\.|skr\.)\s+'
    r'[A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń\w\s]{2,30}\s+'
    r'\d{1,3}[a-z]?(/\d{1,3})?\b',
    re.IGNORECASE
)

# Name preceded by a medical context keyword
_NAME_TRIGGERS = re.compile(
    r'(Pacjent\s*:|Imię\s+i\s+nazwisko\s*:|Nazwisko\s*:|Imię\s*:|'
    r'Pacjent\s*:|PESEL\s*:.*?\n.*?)\s*'
    r'([A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń]{2,}\s+[A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń]{2,})',
    re.IGNORECASE
)


def anonymize(text: str) -> str:
    # Multi-line PESEL first (before single-line, which won't match split ones)
    text = _PESEL_SPLIT.sub('[PESEL]', text)
    text = _PESEL.sub('[PESEL]', text)
    text = _NIP.sub('[NIP]', text)
    text = _PHONE.sub('[TEL]', text)
    text = _EMAIL.sub('[EMAIL]', text)
    text = _STREET.sub('[ADRES]', text)
    text = _DATE_BIRTH.sub(lambda m: m.group(1) + '[DATA_UR]', text)
    text = _NAME_TRIGGERS.sub(lambda m: m.group(1) + ' [PACJENT]', text)
    return text
