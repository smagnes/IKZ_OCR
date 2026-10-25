"""
Lokalny ekstraktor struktury z tekstu OCR — zero zewnętrznych API.
Wyciąga dane medyczne do czystego JSON.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional


def extract_structured(text: str, doc_type: str = "unknown") -> Dict[str, Any]:
    detected = _detect_type(text) if doc_type == "unknown" else doc_type
    return {
        "doc_type": detected,
        "results": _extract_results(text),
        "medications": _extract_medications(text),
        "dates": _extract_dates(text),
        "facility": _extract_facility(text),
        "raw_text": text,
    }


def _detect_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["recepta", "rp.", "przepisane leki", "rpw"]):
        return "recepta"
    if any(w in t for w in ["wynik", "badanie", "norma", "mg/dl", "iu/l", "mmol",
                              "tsh", "ft3", "ft4", "morfologia", "lipidogram",
                              "glukoza", "kreatynina", "hemoglobina"]):
        return "wyniki_badan"
    if any(w in t for w in ["skierowanie", "kieruję", "kieruje", "skierowanie do"]):
        return "skierowanie"
    if any(w in t for w in ["epikryza", "wypis", "hospitalizacja", "karta wypisu"]):
        return "karta_wypisu"
    return "dokument_medyczny"


# ── Lab results ───────────────────────────────────────────────────────────────

# Specific Polish lab test names — ordered longest-first to avoid partial matches
_LAB_NAMES = [
    "Hemoglobina glikowana",
    "Białko C-reaktywne", "Białko całkowite",
    "Glukoza na czczo", "Glukoza",
    "Kreatynina", "Kwas moczowy",
    "Cholesterol całkowity", "Cholesterol LDL", "Cholesterol HDL",
    "Trójglicerydy", "Triglicerydy",
    "Bilirubina całkowita", "Bilirubina",
    "ALT", "AST", "GGTP", "GGT", "ALP", "LDH",
    "Hemoglobina", "Hematokryt",
    "Erytrocyty", "Leukocyty", "Trombocyty", "Płytki krwi",
    "MCV", "MCH", "MCHC", "RDW",
    "Neutrofile", "Limfocyty", "Monocyty", "Eozynofile", "Bazofile",
    "TSH", "FT3", "fT3", "FT4", "fT4", "anty-TPO", "antyTPO",
    "Ferrytyna", "Żelazo", "TIBC", "UIBC",
    "Magnez", "Sód", "Potas", "Chlorki", "Wapń", "Fosfor",
    "Witamina D", "Witamina B12", "Kwas foliowy",
    "INR", "APTT", "Fibrynogen", "D-dimer",
    "PSA", "AFP", "CEA", "CA 125", "CA 19-9",
    "Mocznik", "Sód", "Potas",
    "eGFR", "GFR",
    "HbA1c",
]
_LAB_PATTERN = re.compile(
    r'(' + '|'.join(re.escape(n) for n in _LAB_NAMES) + r')'
    r'\s*[:\|]?\s*([\d,\.]+)\s*([a-zA-Z/%µ][a-zA-Z/%µ\d\.\*]*(?:/[a-zA-Z\d]+)?)\s*'
    r'(?:([\d,\.]+-[\d,\.]+))?\s*([LHlh\*])?',
    re.IGNORECASE
)

# Generic row pattern as fallback
_GENERIC_PATTERN = re.compile(
    r'^([ \t]*[A-ZŻŹĆĄŚĘŁÓŃ][A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ][A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ\s\(\)/\-]{1,38}?)\s+'
    r'([\d,\.]+)\s+'
    r'([a-zA-Z/%µ][a-zA-Z/%µ\d\.\*]*(?:/[a-zA-Z\d]+)?)\s*'
    r'(?:([\d,\.]+-[\d,\.]+))?\s*([LHlh\*])?$',
    re.MULTILINE
)

_SKIP_NAMES = frozenset([
    'data', 'pesel', 'wiek', 'kod', 'data ur', 'nr', 'nip', 'tel', 'fax',
    'adres', 'lekarz', 'pacjent', 'gabinet', 'pieczatka', 'podpis',
])


def _clean_name(name: str) -> str:
    return name.replace('\n', ' ').strip().rstrip('.:')


def _extract_results(text: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    seen: set = set()

    def _add(name, value, unit, rng, flag):
        name = _clean_name(name)
        key = name.lower()
        if len(name) < 3 or key in _SKIP_NAMES or key in seen:
            return
        seen.add(key)
        # Normalize Unicode arrows/symbols to ASCII flags
        if flag in ('⇑', '↑', 'H', 'h'):
            flag_norm = 'H'
        elif flag in ('⇓', '↓', 'L', 'l'):
            flag_norm = 'L'
        else:
            flag_norm = None
        results.append({
            "name": name,
            "value": value.replace(',', '.'),
            "unit": unit,
            "range": rng or None,
            "flag": flag_norm,
        })

    # Polish hospital table format:
    # "Nazwa bad.   Wynik   Zakres ref.   J. miary   Uwagi"
    # "Glukoza      105     70 - 99       mg/dL       ⇑"
    _TABLE_ROW = re.compile(
        r'^[ \t]*([A-ZŻŹĆĄŚĘŁÓŃ][A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ][A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ\s\(\)/\-]{0,38}?)'
        r'[ \t]{2,}([\d,\.]+)'
        r'[ \t]+([\d,\.]+ ?- ?[\d,\.]+)'
        r'[ \t]+([a-zA-Z/%µ][a-zA-Z/%µ\d\.\*]*(?:/[a-zA-Z\d]+)?)'
        r'[ \t]*(⇑|⇓|↑|↓|[LHlh&])?',
        re.MULTILINE
    )

    for m in _TABLE_ROW.finditer(text):
        flag_raw = (m.group(5) or '').strip()
        _add(m.group(1), m.group(2), m.group(4), m.group(3).replace(' ', ''), flag_raw)

    # Specific named-test patterns
    for m in _LAB_PATTERN.finditer(text):
        _add(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5) or "")

    # Generic fallback for remaining lines
    for m in _GENERIC_PATTERN.finditer(text):
        name = _clean_name(m.group(1))
        if name.lower() not in seen:
            _add(name, m.group(2), m.group(3), m.group(4), m.group(5) or "")

    return results


# ── Medications ───────────────────────────────────────────────────────────────

def _extract_medications(text: str) -> List[Dict[str, Any]]:
    meds = []
    pattern = re.compile(
        r'([A-ZŻŹĆĄŚĘŁÓŃ][a-ząęółśżźćń]{3,}(?:\s+[A-Za-z]{2,})?)\s+'
        r'(\d+\s*(?:mg|µg|mcg|ml|g|IU|j\.m\.))\s*'
        r'(?:(\d+)\s*(?:tabletek|tabl\.?|kaps\.?|amp\.?|szt\.?|ml))?',
        re.MULTILINE
    )
    seen = set()
    for m in pattern.finditer(text):
        name = m.group(1).strip()
        key = name.lower()
        if key in seen or len(name) < 4:
            continue
        seen.add(key)
        meds.append({
            "name": name,
            "dose": m.group(2).strip(),
            "quantity": m.group(3) or None,
        })
    return meds


# ── Dates ─────────────────────────────────────────────────────────────────────

def _extract_dates(text: str) -> List[str]:
    # ISO-ish: 2020-12-14, 2020.12.14, 2020/12/14
    hits = re.findall(
        r'\b(20\d{2}[-./](0[1-9]|1[0-2])[-./](0[1-9]|[12]\d|3[01]))\b',
        text
    )
    dates = [d[0] for d in hits]
    # Also PL format: 14.12.2020
    hits2 = re.findall(
        r'\b(0[1-9]|[12]\d|3[01])\.(0[1-9]|1[0-2])\.(20\d{2})\b',
        text
    )
    for d, m, y in hits2:
        iso = f"{y}-{m}-{d}"
        if iso not in dates:
            dates.append(iso)
    return sorted(set(dates))


# ── Facility ──────────────────────────────────────────────────────────────────

def _extract_facility(text: str) -> Optional[str]:
    patterns = [
        # Well-known chains
        r'\b(ALAB(?:\s+Laboratoria)?|Synevo|Diagnostyka|Medicover|LUX\s*MED|Luxmed'
        r'|Euromedic|Carolina Medical|Damian|CML|NZOZ|NZPL)\b',
        # Generic types (greedy up to 60 chars, stop at newline)
        r'(Szpital\s+[^\n]{5,50})',
        r'(Poradnia\s+[^\n]{5,50})',
        r'(Centrum\s+Medyczne\s+[^\n]{5,40})',
        r'(Laboratorium\s+[^\n]{5,50})',
        r'(Przychodnia\s+[^\n]{5,50})',
        r'(Zakład\s+Diagnostyki\s+[^\n]{5,50})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:80]
    return None
