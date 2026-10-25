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

# Alab/Synevo style: "Name (possibly long)   value unit   lo — hi"
# value+unit together, range last, em-dash or regular dash in range
# Name may contain digits (e.g. "FT3", "CA 125"), parens, slashes
_ALAB_PATTERN = re.compile(
    r'^[ \t]*\*?[ \t]*([A-ZŻŹĆĄŚĘŁÓŃ][A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ][A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ \d\(\)/\-\.]{3,65}?)'
    r'[ \t]{3,}([\d,\.]+)[ \t]+([a-zA-Z/%\xb5][a-zA-Z/%\xb5\d\.\*]*(?:/[a-zA-Z\d]+)?)'
    r'[ \t]{2,}([\d,\.]+ ?[—–\-] ?[\d,\.]+|< ?[\d,\.]+)',
    re.MULTILINE
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
    'sprawozdanie', 'nazwa bad', 'wynik badania', 'zakres', 'j. miary',
    'powyżej', 'poniżej', 'wartościreferencyjne', 'uwagi', 'interpret',
])

# Units that are definitely not medical (Polish city names, etc.)
_UNIT_BLACKLIST = frozenset([
    'bydgoszcz', 'warszawa', 'toruń', 'kraków', 'gdańsk', 'poznań',
    'wrocław', 'łódź', 'lublin', 'katowice', 'torun', 'lat', 'lata', 'roku',
])

_VALID_UNIT = re.compile(
    r'^([a-zA-Z]{1,6}(/[a-zA-Z]{1,4})?|[µ%][a-zA-Z]{0,4}|[a-zA-Z]{1,4}\d?)$'
)

# Lab names (lowercase) used for multi-line Syntetyk detection
_LAB_NAMES_LOWER = frozenset(n.lower() for n in _LAB_NAMES)

_RE_VALUE = re.compile(r'^[\d,\.]+$')
_RE_RANGE = re.compile(r'^[\d,\.]+ ?[—–\-] ?[\d,\.]+$')
_RE_UNIT = re.compile(r'^[a-zA-Z/%µ][a-zA-Z/%µ\d\.\*/]*$')
_RE_FLAG = re.compile(r'^[LHlh⇑⇓↑↓]')


def _clean_name(name: str) -> str:
    return name.replace('\n', ' ').strip().rstrip('.:')


def _parse_multiline_table(text: str, add_fn) -> None:
    """
    Syntetyk/Rydgier format: each column on a separate line.
      Glukoza        <- name (may span 2 lines, e.g. "Cholesterol\ncalkowity")
      105            <- value (pure number)
      70 - 99        <- range
      mg/dL          <- unit
      ⇑ (optional)  <- flag
    Triggered only when we see a header row "Wynik" / "Zakres ref." / "J. miary".
    """
    if not re.search(r'Zakres ref\.|J\. miary|Nazwa bad\.', text, re.IGNORECASE):
        return

    lines = [l.strip() for l in text.split('\n')]
    # State machine: collect (name, value, range, unit, flag) tuples
    # A "name" line = known lab name OR a capitalised word that is NOT a number/unit/range
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this line IS a known lab name
        if line.lower() in _LAB_NAMES_LOWER or (
            re.match(r'^[A-ZŻŹĆĄŚĘŁÓŃ][A-Za-ząęółśżźćńĄĘÓŁŚŻŹĆŃ]', line)
            and not _RE_VALUE.match(line)
            and not _RE_RANGE.match(line)
            and not _RE_UNIT.match(line)
            and len(line) >= 3
            and len(line) <= 40
        ):
            name_parts = [line]
            j = i + 1
            # Consume optional name continuation (lowercase or mixed continuation, not a number)
            if j < len(lines):
                nxt = lines[j]
                if (nxt and not _RE_VALUE.match(nxt) and not _RE_RANGE.match(nxt)
                        and not _RE_UNIT.match(nxt) and len(nxt) <= 30
                        and re.match(r'^[a-ząęółśżźćńA-Z]', nxt)):
                    name_parts.append(nxt)
                    j += 1
            # Next must be a value
            if j < len(lines) and _RE_VALUE.match(lines[j]):
                value = lines[j]; j += 1
                rng = ""
                unit = ""
                flag = ""
                if j < len(lines) and _RE_RANGE.match(lines[j]):
                    rng = lines[j].replace(' ', ''); j += 1
                if j < len(lines) and _RE_UNIT.match(lines[j]):
                    unit = lines[j]; j += 1
                if j < len(lines) and _RE_FLAG.match(lines[j]):
                    f = lines[j][0]; j += 1
                    flag = f if f in ('H', 'h', 'L', 'l', '⇑', '⇓', '↑', '↓') else ""
                name = ' '.join(name_parts)
                add_fn(name, value, unit, rng, flag)
                i = j
                continue
        i += 1


_NOISE_LINES = re.compile(
    r'(?:WARTOŚCI\s*REFERENCYJNE|Wartości\s*ref\.?|WYNIKI REFERENCYJNE'
    r'|BADANIE\s+WYNIK|NAZWA\s+BAD|J\.\s*MIARY|WYNIK\s+BADANIA)',
    re.IGNORECASE
)


def _extract_results(text: str) -> List[Dict[str, Any]]:
    # Strip lines that start with known noise (reference-range headers, duplicates)
    text = '\n'.join(
        '' if _NOISE_LINES.match(ln.lstrip()) else ln
        for ln in text.split('\n')
    )
    results: List[Dict[str, Any]] = []
    seen: set = set()

    def _add(name, value, unit, rng, flag):
        name = _clean_name(name)
        key = name.lower()
        if len(name) < 3 or key in _SKIP_NAMES or key in seen:
            return
        # Skip names where first word is all-caps (column headers, noise)
        first_word = name.split()[0] if name.split() else ''
        if first_word.isupper() and len(first_word) > 3:
            return
        # Convert single-char H/L unit to flag (hospital tables with no explicit unit)
        if unit and unit.strip().upper() in ('H', 'L') and not flag:
            flag = unit.strip().upper()
            unit = ""
        # Skip truly garbage units (single non-flag letter)
        elif unit and len(unit.strip()) == 1 and unit.strip().upper() not in ('H', 'L', '%'):
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

    # ── 1. Polish hospital table (Szpital Powiatowy): one row per line
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

    # ── 2. Alab/Synevo inline: "Name (long)   value unit   range"
    for m in _ALAB_PATTERN.finditer(text):
        name = _clean_name(m.group(1))
        # strip leading asterisk/star markers
        name = name.lstrip('* ').strip()
        _add(name, m.group(2), m.group(3), m.group(4), "")

    # ── 3. Syntetyk multi-line: each column on its own line
    _parse_multiline_table(text, _add)

    # ── 4. Specific named-test patterns
    for m in _LAB_PATTERN.finditer(text):
        _add(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5) or "")

    # ── 5. Generic fallback for remaining lines
    for m in _GENERIC_PATTERN.finditer(text):
        name = _clean_name(m.group(1))
        key = name.lower()
        unit = m.group(3).lower() if m.group(3) else ""
        # Skip city fragments or non-medical units
        if any(city in key for city in ('bydgoszcz', 'warszawa', 'toruń', 'kraków',
                                         'gdańsk', 'poznań', 'wrocław', 'łódź')):
            continue
        if unit in _UNIT_BLACKLIST:
            continue
        if key not in seen:
            _add(name, m.group(2), m.group(3), m.group(4), m.group(5) or "")

    return results


# ── Medications ───────────────────────────────────────────────────────────────

_MED_FALSE_POSITIVES = frozenset(
    n.lower() for n in _LAB_NAMES
) | frozenset([
    'triglicerydy', 'trójglicerydy', 'glukoza', 'kreatynina', 'hemoglobina',
    'cholesterol', 'bilirubina', 'ferrytyna', 'witamina', 'leukocyty',
    'erytrocyty', 'trombocyty', 'neutrofile', 'limfocyty', 'monocyty',
    # street/city fragments
    'nadolska', 'królewska', 'jadwigi', 'grudziądzka', 'stępińska',
])


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
        if key in seen or len(name) < 4 or key in _MED_FALSE_POSITIVES:
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
