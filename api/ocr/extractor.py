"""
Lokalny ekstraktor struktury z tekstu OCR — zero zewnętrznych API.
Wyciąga dane medyczne do czystego JSON.
"""
import re
from typing import Any


def extract_structured(text: str, doc_type: str = "unknown") -> dict:
    return {
        "doc_type": _detect_type(text) if doc_type == "unknown" else doc_type,
        "results": _extract_results(text),
        "medications": _extract_medications(text),
        "dates": _extract_dates(text),
        "facility": _extract_facility(text),
        "raw_text": text,
    }


def _detect_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["recepta", "rp.", "przepisane leki"]):
        return "recepta"
    if any(w in t for w in ["wynik", "badanie", "norma", "mg/dl", "iu/l", "mmol"]):
        return "wyniki_badan"
    if any(w in t for w in ["skierowanie", "kieruję", "kieruje"]):
        return "skierowanie"
    if any(w in t for w in ["epikryza", "wypis", "hospitalizacja"]):
        return "karta_wypisu"
    return "dokument_medyczny"


def _extract_results(text: str) -> list[dict]:
    """Wyciąga wiersze wyników badań: nazwa | wartość | jednostka | zakres | flaga"""
    results = []
    # Wzorzec: tekst liczba jednostka opcjonalnie zakres flaga
    pattern = re.compile(
        r'([A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ][A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ\s\(\)/]{3,40}?)\s+'
        r'([\d,\.]+)\s*'
        r'([a-zA-Z/%µ][a-zA-Z/%µ\d\.\*]*(?:/[a-zA-Z\d]+)?)\s*'
        r'(?:([\d,\.]+-[\d,\.]+))?\s*'
        r'([LHlh\*])?',
        re.MULTILINE
    )
    for m in pattern.finditer(text):
        name = m.group(1).strip()
        if len(name) < 3 or name.lower() in ('data', 'pesel', 'wiek', 'kod'):
            continue
        results.append({
            "name": name.replace('\n', ' ').strip(),
            "value": m.group(2).replace(',', '.'),
            "unit": m.group(3),
            "range": m.group(4) or None,
            "flag": m.group(5).upper() if m.group(5) else None,
        })
    return results


def _extract_medications(text: str) -> list[dict]:
    """Wyciąga leki z recept"""
    meds = []
    # Wzorzec: nazwa leku + dawka + ilość
    pattern = re.compile(
        r'([A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń]{3,}(?:\s+[A-Za-z]{2,})?)\s+'
        r'(\d+\s*(?:mg|µg|mcg|ml|g|IU))\s*'
        r'(?:(\d+)\s*(?:tabletek|kaps|amp|szt|ml))?',
        re.MULTILINE
    )
    for m in pattern.finditer(text):
        meds.append({
            "name": m.group(1).strip(),
            "dose": m.group(2),
            "quantity": m.group(3) or None,
        })
    return meds


def _extract_dates(text: str) -> list[str]:
    dates = re.findall(
        r'\b(20\d{2}[-./](0[1-9]|1[0-2])[-./](0[1-9]|[12]\d|3[01]))\b',
        text
    )
    return [d[0] for d in dates]


def _extract_facility(text: str):
    patterns = [
        r'(Szpital\s+[\w\s]+)',
        r'(Poradnia\s+[\w\s]+)',
        r'(Laboratorium\s+[\w\s]+)',
        r'(ALAB|Synevo|Diagnostyka|Medicover|LUX MED|Luxmed)',
        r'(Centrum\s+Medyczne\s+[\w\s]+)',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:80]
    return None
