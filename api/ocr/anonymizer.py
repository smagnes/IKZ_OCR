import re

# Wzorce PL danych osobowych
_PESEL = re.compile(r'\b\d{11}\b')
_NIP   = re.compile(r'\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b')
# Data urodzenia tylko po keywordzie "ur" lub "urodzenia" lub "birth"
_DATE_BIRTH = re.compile(r'(ur\.?\s*:?\s*|data\s+ur[oó]dze\w*\s*:?\s*)((?:19|20)\d{2}[-./]\d{2}[-./]\d{2})', re.IGNORECASE)
_PHONE = re.compile(r'(\+48[\s-]?)?\b\d{3}[\s-]?\d{3}[\s-]?\d{3}\b')
_EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
_STREET = re.compile(
    r'\b(ul\.|al\.|pl\.|os\.|skr\.)\s+[A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń\w\s]{2,30}\s+\d{1,3}[a-z]?(/\d{1,3})?\b',
    re.IGNORECASE
)
# Imię + Nazwisko (dwie duże litery z rzędu, min 3 znaki każde)
_NAME = re.compile(
    r'\b([A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń]{2,})\s+([A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń]{2,})\b'
)

# Słowa kluczowe przy których następuje imię/nazwisko w dokumentach medycznych
_NAME_TRIGGERS = re.compile(
    r'(Pacjent:|Imię i nazwisko:|Nazwisko:|Pacjent\s*:|Imię:|PESEL:.*?\n.*?)\s*'
    r'([A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń]{2,}\s+[A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń]{2,})',
    re.IGNORECASE
)


def anonymize(text: str) -> str:
    text = _PESEL.sub('[PESEL]', text)
    text = _NIP.sub('[NIP]', text)
    text = _PHONE.sub('[TEL]', text)
    text = _EMAIL.sub('[EMAIL]', text)
    text = _STREET.sub('[ADRES]', text)
    text = _DATE_BIRTH.sub(lambda m: m.group(1) + '[DATA_UR]', text)
    text = _NAME_TRIGGERS.sub(lambda m: m.group(1) + ' [PACJENT]', text)
    return text
