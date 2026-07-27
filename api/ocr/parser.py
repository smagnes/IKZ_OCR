import re
from schemas import DocType, ScanAlert

# PESEL: labeled (before or after) or bare 11-digit with birth month validation
_PESEL_RE = re.compile(r"PESEL[:\s]+(\d{11})", re.I)
_PESEL_REVERSE_RE = re.compile(r"(\d{11})\s*\nPESEL", re.I)   # value before label (OCR columns)
_PESEL_BARE_RE = re.compile(r"(?<![/\d])(\d{11})(?!\d)")
_DATE_RE = re.compile(
    r"\b("
    r"\d{4}-\d{2}-\d{2}"          # YYYY-MM-DD (ISO, lab systems)
    r"|"
    r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}"  # DD.MM.YYYY / DD-MM-YY etc.
    r")\b"
)
_DOCTOR_RE = re.compile(r"lek\.\s*med\.\s+([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]+\s+[A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]+)")
# Patient: label then name ON THE SAME LINE (space-only separator, no newlines)
_PATIENT_RE = re.compile(
    r"(?:Pacjent *: *|Imię i nazwisko *: *|Nazwisko i imię *: *)"
    r"([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]{2,} +[A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]{2,})"
)
# Szpital Powiatowy Iława: "Imię: ANNA KRYSTYNA   Nazwisko: ŚNIADKOWSKA" (same line or split)
_PATIENT_IMIE_INLINE_RE = re.compile(
    r"Imi(?:ę|e)\s*:\s*([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń ]+?)\s{2,}"
    r"Nazwisko\s*:\s*([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]+)",
    re.I
)
_PATIENT_IMIE_MULTILINE_RE = re.compile(
    r"Imi(?:ę|e)\s*:?\s*\n([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń ]+)\n"
    r"(?:[^\n]*\n)?"
    r"Nazwisko\s*:?\s*\n([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]+)",
    re.I
)
# Surya column scramble: "Imię:" and "Nazwisko:" appear on separate, non-adjacent lines.
# Stop at 2+ spaces (column boundary in reconstructed layout) to avoid capturing right-column noise.
_IMIE_ONLY_RE = re.compile(
    r"Imi(?:ę|e)\s*:\s*"
    r"([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]+"
    r"(?:[ ][A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]+)*)"
    r"(?:[ ]{2,}|\s*\n|$)",
    re.I
)
_NAZWISKO_ONLY_RE = re.compile(
    r"Nazwisko\s*:\s*([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń]+)",
    re.I
)
# Patient name split across two lines after label (np. label\nSZYSZKOWSKA\nGENOWEFA)
_PATIENT_MULTILINE_RE = re.compile(
    r"(?:Nazwisko i imię|Imię i nazwisko|Pacjent)\s*:?\s*\n([A-ZŁÓŚĄŹŻĆŃ]{2,})\n([A-ZŁÓŚĄŹŻĆŃ]{2,})",
    re.I
)
# Patient name BEFORE label (OCR column scramble: SZYSZKOWSKA\nNazwisko i imię:\nGENOWEFA)
_PATIENT_LABEL_MIDDLE_RE = re.compile(
    r"([A-ZŁÓŚĄŹŻĆŃ]{2,})\n(?:Nazwisko i imię|Imię i nazwisko)\s*:?\s*\n([A-ZŁÓŚĄŹŻĆŃ]{2,})",
    re.I
)
# Szpital pdftotext: "Nazwisko i imię:      SZYSZKOWSKA\n      GENOWEFA"
_PATIENT_SZPITAL_PDF_RE = re.compile(
    r"(?:Nazwisko i imię|Imię i nazwisko)\s*:\s+([A-ZŁÓŚĄŹŻĆŃ]{2,})\s*\n"
    r"[ \t]+([A-ZŁÓŚĄŹŻĆŃ]{2,})",
    re.I
)
# ALAB: patient name on own line, no label, immediately before PESEL block (mixed case)
_PATIENT_BEFORE_PESEL_RE = re.compile(
    r"^\s*([A-ZŁÓŚĄŹŻĆŃ][a-złóśąźżćń]{2,}\s+[A-ZŁÓŚĄŹŻĆŃ][a-złóśąźżćń]{2,})\s*\n"
    r"(?:[^\n]*\n){0,5}[^\n]*PESEL",
    re.I | re.M
)
_PATIENT_BEFORE_RE = re.compile(
    r"([A-ZŁÓŚĄŹŻĆŃ]{2,} +[A-ZŁÓŚĄŹŻĆŃ]{2,})\n(?:[^\n]*\n){1,4}Pacjent:",
    re.M
)
_FACILITY_RE = re.compile(
    r"(?:(?:Powiatowy|Wojew[a-złóśąźżćń]+|Miejski|Regionalny|Centraln\w*)\s+)?"
    r"(?:Szpital|Centrum|Klinika|Przychodnia|Zakład|Punkt Pobrań|Laboratorium|NZOZ|SPZOZ|ALAB)\s+[^\n]{3,60}",
    re.I
)
# Specific exam date labels (more reliable than grabbing the first date in text)
_EXAM_DATE_RE = re.compile(
    r"(?:Data wykonania badania|Data wykonania|Data badania|Data zlecenia)\s*[:/]?\s*"
    r"(\d{1,2}[-./]\d{1,2}[-./]\d{2,4}|\d{4}-\d{2}-\d{2})",
    re.I
)

# OPTIMed table row: "Param Name (min:X max:Y^) [unit]" — value on next line
# Handles: empty min/max, special units like [10x3/µl], text like [%]
_OPTIMED_PARAM_RE = re.compile(
    r'^([\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ][^(\n]{2,55}?)'   # param name (Polish chars)
    r'\s*\(\s*(?:min:([0-9.,]*)\s+)?'              # optional min:
    r'max:([0-9.,]*)\^?\s*\)'                       # max: (may be empty)
    r'(?:\s*\[([^\]]{1,20})\])?'                   # optional [unit]
    r'\s*$',
    re.I | re.M
)

# Acceptable value formats from OPTIMed tables
_OPTIMED_VALUE_RE = re.compile(
    r'^('
    r'\d[\d,. ;/<>±]*'          # numeric (with Polish comma decimal)
    r'|>[0-9,.]+'               # >60 etc
    r'|<[0-9,.]+'               # <0.5 etc
    r'|żółta|zupełna|przejrzysta|mętna'
    r'|nieobecn[ae]?|w normie|ujemn[ya]|dodatni[a]?'
    r'|nieliczn[e]?|liczn[e]?|liczne|nieliczne'
    r')$',
    re.I
)

# Clinical alert thresholds for OPTIMed parameters
_ALERT_RULES: list[tuple[str, str, float, str]] = [
    # (keyword_in_param, direction, threshold, alert_name)
    ("glukoza",      "high", 5.5,  "hiperglikemia"),
    ("hemoglobin",   "low",  11.5, "anemia"),
    ("leukocyt",     "high", 10.0, "leukocytoza"),   # Leukocyty [tys/µl]
    ("neutrofil",    "high", 80.0, "leukocytoza"),   # neutrofilia → often infection
    ("tsh",          "high", 4.5,  "niedoczynnosc_tarczycy"),
    ("tsh",          "low",  0.4,  "nadczynnosc_tarczycy"),
    ("troponin",     "high", 99.0, "pilne"),          # troponin 99th percentile cutoff
    ("bilirubina ca","high", 21.0, "pilne"),
]


def _mask_pesel(pesel: str) -> str:
    return pesel[:5] + "***" + pesel[8:]


def _extract_common(text: str) -> dict:
    result: dict = {}

    # PESEL: try labeled inline, then reversed (OCR columns), then bare 11-digit
    pesel_match = _PESEL_RE.search(text) or _PESEL_REVERSE_RE.search(text)
    if not pesel_match:
        for m in _PESEL_BARE_RE.finditer(text):
            p = m.group(1)
            month_raw = int(p[2:4])
            month = month_raw - 20 if month_raw > 20 else month_raw
            if 1 <= month <= 12:
                pesel_match = m
                break
    if pesel_match:
        result["pesel_masked"] = _mask_pesel(pesel_match.group(1))

    # Specific exam date labels take priority over first-date-in-text
    exam_m = _EXAM_DATE_RE.search(text)
    if exam_m:
        result["exam_date"] = exam_m.group(1)
    else:
        dates = _DATE_RE.findall(text)
        # Prefer dates with year >= 2000 (birth dates / old records are older)
        exam_date = None
        for d in dates:
            year_m = re.search(r'\d{4}', d)
            if year_m and int(year_m.group()) >= 2000:
                exam_date = d
                break
        if exam_date is None and dates:
            exam_date = dates[0]
        if exam_date:
            result["exam_date"] = exam_date

    doc_match = _DOCTOR_RE.search(text)
    if doc_match:
        result["doctor"] = "lek. med. " + doc_match.group(1).strip()

    # Patient extraction priority (most specific first):
    # 1. "Pacjent: X Y" or "Imię i nazwisko: X Y" — inline same-line label
    # 2. "Imię: X  Nazwisko: Y" — same line, Szpital Powiatowy Iława
    # 3. "Imię:\nX\nNazwisko:\nY" — multi-line OCR scramble
    # 4. "Nazwisko i imię:  SURNAME\n  FIRSTNAME" — pdftotext Szpital Toruń
    # 5. "SZYSZKOWSKA\nNazwisko i imię:\nGENOWEFA" — Surya column scramble
    # 6. "Nazwisko i imię:\nSZYSZKOWSKA\nGENOWEFA" — multi-line after label
    # 7. ALAB mixed-case name before PESEL block
    # 8. ALL-CAPS name before "Pacjent:" label
    for pat, groups in [
        (_PATIENT_RE,               lambda m: m.group(1).strip()),
        (_PATIENT_IMIE_INLINE_RE,   lambda m: f"{m.group(1).strip()} {m.group(2).strip()}"),
        (_PATIENT_IMIE_MULTILINE_RE,lambda m: f"{m.group(1).strip()} {m.group(2).strip()}"),
        (_PATIENT_SZPITAL_PDF_RE,   lambda m: f"{m.group(1).strip()} {m.group(2).strip()}"),
        (_PATIENT_LABEL_MIDDLE_RE,  lambda m: f"{m.group(1).strip()} {m.group(2).strip()}"),
        (_PATIENT_MULTILINE_RE,     lambda m: f"{m.group(1).strip()} {m.group(2).strip()}"),
        (_PATIENT_BEFORE_PESEL_RE,  lambda m: m.group(1).strip()),
        (_PATIENT_BEFORE_RE,        lambda m: m.group(1).strip()),
    ]:
        m = pat.search(text)
        if m:
            result["patient"] = groups(m)
            break
    # Fallback: Surya column scramble — "Imię:" and "Nazwisko:" on non-adjacent lines
    if "patient" not in result:
        imie_m = _IMIE_ONLY_RE.search(text)
        nazw_m = _NAZWISKO_ONLY_RE.search(text)
        if imie_m and nazw_m:
            result["patient"] = f"{imie_m.group(1).strip()} {nazw_m.group(1).strip()}"
        elif imie_m:
            result["patient"] = imie_m.group(1).strip()

    fac_match = _FACILITY_RE.search(text)
    if fac_match:
        result["facility"] = fac_match.group(0).strip()

    return result


# ── UNIVERSAL OPTIMED TABLE EXTRACTOR ────────────────────────────────────────

def _generate_alert(param_lower: str, val: float, direction: str, alerts: list) -> None:
    for kw, dir_, threshold, alert in _ALERT_RULES:
        if kw in param_lower and dir_ == direction:
            if direction == "high" and val > threshold and alert not in alerts:
                alerts.append(alert)
            elif direction == "low" and val < threshold and alert not in alerts:
                alerts.append(alert)


def _extract_optimed_labs(text: str) -> tuple[dict, list[str]]:
    """
    Universal extractor for System OPTIMed lab tables.
    Each row format: "Parametr (min:X max:Y^) [unit]"  followed by value on next line.
    Extracts ALL parameters, compares to reference range, adds ↑/↓ and clinical alerts.
    """
    fields: dict = {}
    alerts: list[str] = []
    lines = text.split('\n')

    for i, line in enumerate(lines):
        stripped = line.strip()
        m = _OPTIMED_PARAM_RE.match(stripped)
        if not m:
            continue

        param_name = m.group(1).strip().rstrip(' -–')
        min_str    = (m.group(2) or '').replace(',', '.')
        max_str    = (m.group(3) or '').replace(',', '.')
        unit       = (m.group(4) or '').strip()

        # Skip obvious section headers and non-parameter lines
        if len(param_name) < 3 or param_name.lower() in ('wynik', 'data', 'opis'):
            continue

        # Find value on the next 1-3 non-empty lines
        value_str = None
        for j in range(i + 1, min(i + 4, len(lines))):
            candidate = lines[j].strip()
            if not candidate:
                continue
            if _OPTIMED_VALUE_RE.match(candidate):
                value_str = candidate
            break  # stop at first non-empty line regardless

        if value_str is None:
            continue

        # Build display key: "Param [unit]" or just "Param"
        key = f"{param_name} [{unit}]" if unit else param_name

        # Numeric comparison for ↑/↓
        indicator = ''
        param_lower = param_name.lower()
        try:
            # Handle "X; Y" (e.g. CRP: "0,60; 0,70") — take first number
            num_part = re.split(r'[;]', value_str)[0].strip()
            val = float(num_part.replace(',', '.'))

            if max_str:
                try:
                    mx = float(max_str)
                    if val > mx:
                        indicator = ' ↑'
                        _generate_alert(param_lower, val, 'high', alerts)
                except ValueError:
                    pass

            if min_str and not indicator:
                try:
                    mn = float(min_str)
                    if val < mn:
                        indicator = ' ↓'
                        _generate_alert(param_lower, val, 'low', alerts)
                except ValueError:
                    pass

        except (ValueError, TypeError):
            pass  # text values like "żółta", "w normie" — no comparison

        fields[key] = value_str + indicator

    return fields, alerts


# ── CONTEXT-BASED LAB EXTRACTOR ──────────────────────────────────────────────
# Surya OCR reads multi-column tables column-by-column, so values appear
# BEFORE or AFTER parameter names on separate lines. We find known param names
# and collect the numeric value from surrounding lines.

_KNOWN_LAB_PARAMS: list[tuple[str, str]] = [
    ("Cholesterol całkowity",   "cholesterol ca"),
    ("Cholesterol HDL",         "cholesterol hdl"),
    ("Cholesterol LDL",         "cholesterol ldl"),
    ("Trójglicerydy",           "trojgliceryd"),
    ("Trójglicerydy",           "trójgliceryd"),
    ("Glukoza",                 "glukoza"),
    ("Kwas moczowy",            "kwas moczowy"),
    ("Kreatynina",              "kreatynin"),
    ("Mocznik",                 "mocznik"),
    ("Sód",                     "sód"),
    ("Potas",                   "potas"),
    ("Bilirubina całkowita",    "bilirubina ca"),
    ("Bilirubina bezpośrednia", "bilirubina bez"),
    ("ALT (ALAT)",              "alt"),
    ("AST (ASAT)",              "ast"),
    ("GGT",                     "ggt"),
    ("Albuminy",                "albumin"),
    ("Białko całkowite",        "białko"),
    ("Hemoglobina",             "hemoglobin"),
    ("Erytrocyty",              "erytrocyt"),
    ("Leukocyty",               "leukocyt"),
    ("Płytki krwi",             "płytki"),
    ("TSH",                     "tsh"),
    ("FT3",                     "ft3"),
    ("FT4",                     "ft4"),
    ("CRP",                     "crp"),
    ("Ferrytyna",               "ferrytyn"),
    ("Żelazo",                  "żelazo"),
    ("Wapń",                    "wapń"),
    ("Witamina B12",            "witamina b12"),
    ("Witamina D",              "witamina d"),
    # Morfologia parametry (w wynikach szpitalnych pojawiają się w tabeli lab)
    ("Hematokryt",              "hematokryt"),
    ("MCV",                     "mcv"),
    ("MCH",                     "mch"),
    ("MCHC",                    "mchc"),
    ("Erytrocyty",              "erytrocyt"),
    ("Leukocyty",               "leukocyt"),
    ("Płytki krwi",             "płytki"),
    ("Neutrofile",              "neutrofil"),
    ("Limfocyty",               "limfocyt"),
    # Koagulologia
    ("APTT",                    "aptt"),
    ("APTT",                    "appt"),
    ("PT",                      "pt "),
    ("INR",                     "inr"),
    # Enzymy — aliasy szpitalne
    ("AST (ASAT)",              "asp"),   # niektóre systemy piszą ASP zamiast AST
    ("Amylaza",                 "amylaz"),
    ("Lipaza",                  "lipaz"),
    # Dodatkowe biochemia
    ("Magnez",                  "magnez"),
    ("Fosfor",                  "fosfor"),
    ("Chlorki",                 "chlork"),
    ("HbA1c",                   "hba1c"),
    ("PSA",                     "psa"),
    ("AFP",                     "afp"),
    ("CEA",                     "cea"),
    # Hormony tarczycy — pełne nazwy ALAB
    ("TSH",                     "tyreotropin"),
    ("FT3",                     "wolna trijodotyronin"),
    ("FT4",                     "wolna tyroksyn"),
    ("ATG",                     "antytyreoglobulin"),
    ("ATPO",                    "peroksydazie tarczyc"),
    ("ATPO",                    "p/c przeciw peroksydaz"),
    # Hormony płciowe
    ("Estradiol",               "estradiol"),
    ("FSH",                     "fsh"),
    ("LH",                      "lh "),
    ("Progesteron",             "progesteron"),
    ("Testosteron",             "testosteron"),
    ("Prolaktyna",              "prolaktyn"),
    ("DHEA-S",                  "dhea"),
    # Morfologia dodatkowe
    ("PDW",                     "pdw"),
    ("MPV",                     "mpv"),
    ("RDW",                     "rdw"),
    ("NEU% Neutrocyty",         "neu%-"),
    ("NEU# Neutrocyty",         "neu#-"),
    ("LYM% Limfocyty",          "lym%-"),
    ("LYM# Limfocyty",          "lym#-"),
    ("Inne% (Eo,Bazo,Mono)",    "inne%-"),
    ("Inne# (Eo,Bazo,Mono)",    "inne#-"),
    ("P-LCR",                   "p-lcr"),
    # Lipidy — dodatkowe aliasy
    ("HDL cholesterol",         "hdl cholesterol"),
    ("LDL cholesterol",         "ldl cholesterol"),
    ("Sód",                     "sód"),
    ("Sód",                     "sod"),
]

# Format szpitalny: "Glukoza  105  70 - 99  mg/dL  ↑" w jednej linii
# Obsługuje: Surya OCR (↑↓&) oraz pdftotext (⇑⇓& z wiodącymi spacjami)
_SZPITAL_ROW_RE = re.compile(
    r'^[ \t]*'                                                     # opcjonalne wiodące spacje
    r'([A-ZŁÓŚĄŹŻĆŃ][A-ZŁÓŚĄŹŻĆŃa-złóśąźżćń ()/-]{1,40}?)'    # nazwa parametru
    r'\s{2,}'                                                      # 2+ spacje (separator kolumn)
    r'(\d+[,.]?\d*)'                                              # wynik
    r'\s+(\d+[,.]?\d*\s*[-–]\s*\d+[,.]?\d*)'                    # zakres "70 - 99"
    r'\s+(\S+)'                                                    # jednostka
    r'\s+([↑↓⇑⇓&])',                                             # flaga (↑↓ Surya, ⇑⇓ pdftotext)
    re.M
)

# ALAB "Sprawozdanie z badań laboratoryjnych" — row: "[*] Nazwa (ABBR)   value unit   range"
# Column gap is 4+ spaces (pdftotext -layout preserves column alignment)
_ALAB_ROW_RE = re.compile(
    r'^[ \t*]*'
    r'(.+?)'                           # param name (lazy — stops at column gap)
    r'(?=[ \t]{4,})'                   # lookahead: column separator (4+ spaces)
    r'[ \t]{4,}'
    r'([<>]\s*\d+[,.]?\d*|\d+[,.]?\d*)'  # value (optional < or >)
    r'[ \t]+'
    r'(\S+)'                           # unit
    r'(?:[ \t]{3,}(.+?))?'             # optional range
    r'\s*$',
    re.M
)

# Lublin "Laboratorium Diagnostyczne" — row: "Param   value   unit   min   max   flag"
# Flag at end: ~ (normal), H (high), L (low)
_LUBLIN_ROW_RE = re.compile(
    r'^(.+?)[ \t]{4,}'                 # param name
    r'([<>]?\s*\d+[,.]?\d*)[ \t]{2,}' # value
    r'(\S{1,20})[ \t]{2,}'             # unit
    r'(\d+[,.]?\d*)[ \t]{3,}'          # min
    r'(\d+[,.]?\d*)[ \t]{2,}'          # max
    r'([~HL])\s*$',                    # flag
    re.M
)
_LUBLIN_SECTION_RE = re.compile(
    r'^([^\n\-]+?)\s*[-–]\s*(?:SUROWICA|KREW\b|MOCZ\b|PŁYN\b)',
    re.M | re.I
)

_NUM_LINE_RE  = re.compile(r'^\d{1,5}[,.]?\d{0,4}$')
_UNIT_LINE_RE = re.compile(
    r'^(mg/dl|mmol/l|g/dl|g/l|u/l|iu/l|nmol/l|µmol/l|miu/ml|ng/ml|pg/ml|µg/dl|%)$',
    re.I
)
_FLAG_LINE_RE = re.compile(r'^([LH↑↓&]|11|ll|l1|1l|–)$', re.I)


def _flag_to_indicator(flag: str) -> str:
    """Normalize flag symbol to ↑/↓/'' regardless of source format."""
    f = flag.strip()
    if f in ('H', '↑', '⇑', '11', 'll', 'l1', '1l'):  # ↑/⇑ Surya vs pdftotext
        return ' ↑'
    if f in ('L', '↓', '⇓', '–'):                       # ↓/⇓ Surya vs pdftotext
        return ' ↓'
    return ''  # & = w normie, brak flagi


def _extract_szpital_labs(text: str) -> tuple[dict, list[str]]:
    """
    Extractor for hospital row-format tables (Szpital Toruń style).
    Each row: "Nazwa  Wynik  Zakres  Jednostka  Flaga"
    Flags: ↑ (powyżej), ↓ (poniżej), & (w normie)
    """
    fields: dict = {}
    alerts: list[str] = []

    for m in _SZPITAL_ROW_RE.finditer(text):
        param   = m.group(1).strip()
        val_str = m.group(2).strip()
        unit    = m.group(4).strip()
        flag    = m.group(5).strip()

        indicator = _flag_to_indicator(flag)
        key = f"{param} [{unit.lower()}]" if unit else param
        fields[key] = val_str + indicator

        try:
            val = float(val_str.replace(',', '.'))
            direction = 'high' if indicator == ' ↑' else ('low' if indicator == ' ↓' else '')
            if direction:
                _generate_alert(param.lower(), val, direction, alerts)
        except (ValueError, TypeError):
            pass

    return fields, alerts


def _extract_alab_labs(text: str) -> tuple[dict, list[str]]:
    """ALAB 'Sprawozdanie z badań laboratoryjnych' format.
    Row (pdftotext -layout): [*] Full Name (ABBR)   value unit   range
    Uses parenthesised abbreviation as canonical display name when present.
    """
    if 'ALAB' not in text and 'alab' not in text.lower():
        return {}, []

    fields: dict = {}
    alerts: list[str] = []
    _skip = {'nazwa badania', 'badanie', 'wynik', 'materiał', 'wykonali', 'zatwierdzili'}
    # Metadata fields that look like lab rows but aren't
    _meta_prefixes = ('wiek', 'płeć', 'pesel', 'data', 'adres', 'nr/', 'nr ', 'numer',
                      'miejsce', 'lekarz', 'ident', 'zlecenie', 'oddział', 'metoda',
                      'wykon', 'zatwierd', 'bez pisemnej', 'niniejszy', 'osoby',
                      'środowisko', 'podane', 'autoryz')

    for m in _ALAB_ROW_RE.finditer(text):
        raw_name  = m.group(1).strip()
        val_raw   = m.group(2).strip()
        unit      = m.group(3).strip()
        range_str = (m.group(4) or '').strip()

        if raw_name.lower() in _skip or len(raw_name) < 2:
            continue
        # Skip metadata rows: param name ends with colon (e.g. "Wiek:") or is a known header
        if raw_name.endswith(':') or any(raw_name.lower().startswith(p) for p in _meta_prefixes):
            continue
        # Skip rows where "unit" is a metadata keyword rather than a unit
        if unit.rstrip(':').lower() in ('lat', 'lata', 'lat.', 'kobieta', 'mężczyzna', 'k', 'm',
                                        'toruń', 'warszawa', 'kraków', 'łódź', 'zleceniodawca'):
            continue

        # Prefer abbreviation in parentheses as display key (e.g. "(TSH)", "(FT3)")
        abbr_m = re.search(r'\(([A-Z][A-Z0-9-]{1,8})\)', raw_name)
        display = abbr_m.group(1) if abbr_m else raw_name.rstrip(' -')

        # Strip leading < > from value for numeric comparison
        prefix = ''
        val_clean = val_raw
        if val_raw and val_raw[0] in '<>':
            prefix = val_raw[0]
            val_clean = val_raw[1:].strip()

        key = f"{display} [{unit}]" if unit else display
        indicator = ''
        try:
            val = float(val_clean.replace(',', '.'))
            # Parse range: "X,Y — A,B" or "< N" or "> N"
            if range_str.startswith('<'):
                mx_m = re.search(r'[\d,]+', range_str)
                if mx_m:
                    mx = float(mx_m.group().replace(',', '.'))
                    if val > mx:
                        indicator = ' ↑'
                        _generate_alert(display.lower(), val, 'high', alerts)
            elif range_str.startswith('>'):
                mn_m = re.search(r'[\d,]+', range_str)
                if mn_m:
                    mn = float(mn_m.group().replace(',', '.'))
                    if val < mn:
                        indicator = ' ↓'
            elif range_str:
                parts = re.split(r'\s*[—–-]\s*', range_str)
                if len(parts) >= 2:
                    mn = float(re.search(r'[\d,]+', parts[0]).group().replace(',', '.'))
                    mx = float(re.search(r'[\d,]+', parts[-1]).group().replace(',', '.'))
                    if val > mx:
                        indicator = ' ↑'
                        _generate_alert(display.lower(), val, 'high', alerts)
                    elif val < mn:
                        indicator = ' ↓'
                        _generate_alert(display.lower(), val, 'low', alerts)
        except (ValueError, TypeError, AttributeError):
            pass

        fields[key] = prefix + val_clean.replace(',', '.') + indicator

    return fields, alerts


def _extract_lublin_labs(text: str) -> tuple[dict, list[str]]:
    """Laboratorium Diagnostyczne / similar pdftotext format.
    Row: Param   value   unit   min   max   flag  (flag: ~ H L)
    Section headers like 'FT4 - SUROWICA' map to single-param rows 'Wynik w surowicy'.
    """
    if not re.search(r'Zakres ref\.|tys/µl|mln/µl|pmol/l', text):
        return {}, []

    fields: dict = {}
    alerts: list[str] = []
    current_section = ''
    _sub_labels = {'wynik w surowicy', 'wynik badania', 'wynik'}

    for line in text.split('\n'):
        # Detect section header: "FT4 - SUROWICA (ICD-9: O69)"
        sm = _LUBLIN_SECTION_RE.match(line.rstrip())
        if sm:
            current_section = sm.group(1).strip().upper()
            continue

        m = _LUBLIN_ROW_RE.match(line.rstrip())
        if not m:
            continue

        raw_name = m.group(1).strip()
        val_str  = m.group(2).replace(',', '.').strip()
        unit     = m.group(3).strip()
        min_str  = m.group(4).replace(',', '.')
        max_str  = m.group(5).replace(',', '.')
        flag     = m.group(6)

        # Sub-labels like "Wynik w surowicy" → use current section as display name
        if raw_name.lower() in _sub_labels and current_section:
            display = current_section
        else:
            display = raw_name
            current_section = ''  # reset section once we see a named row

        indicator = _flag_to_indicator(flag.replace('~', ''))
        key = f"{display} [{unit}]" if unit else display

        try:
            val = float(re.sub(r'^[<>]\s*', '', val_str))
            if indicator == ' ↑':
                _generate_alert(display.lower(), val, 'high', alerts)
            elif indicator == ' ↓':
                _generate_alert(display.lower(), val, 'low', alerts)
            elif not indicator and min_str and max_str:
                mn, mx = float(min_str), float(max_str)
                if val > mx:
                    indicator = ' ↑'
                    _generate_alert(display.lower(), val, 'high', alerts)
                elif val < mn:
                    indicator = ' ↓'
                    _generate_alert(display.lower(), val, 'low', alerts)
        except (ValueError, TypeError):
            pass

        prefix = '<' if val_str.startswith('<') else (
                 '>' if val_str.startswith('>') else '')
        clean_val = re.sub(r'^[<>]\s*', '', val_str)
        fields[key] = prefix + clean_val + indicator

    return fields, alerts


def _extract_tabular_labs(text: str) -> tuple[dict, list[str]]:
    """
    Context-based extractor for column-scrambled OCR output.
    Finds known Polish lab parameter names and reads values from nearby lines.
    """
    if not re.search(r"Badanie|mg/dl|mmol", text, re.I):
        return {}, []

    fields: dict = {}
    alerts: list[str] = []
    lines = [l.strip() for l in text.split('\n')]
    found: set = set()

    for i, line in enumerate(lines):
        # Strip footnote markers like (1,3,2) or (1,6,5)
        line_clean = re.sub(r'\s*\(\d[,.\d]*\)\s*', '', line).strip()
        line_lower = line_clean.lower()

        matched_display = None
        for display, prefix in _KNOWN_LAB_PARAMS:
            if line_lower.startswith(prefix) and display not in found:
                matched_display = display
                break
        if not matched_display:
            continue
        found.add(matched_display)

        # Window: 6 lines before + 4 lines after the param name
        before = lines[max(0, i - 6):i]
        after  = lines[i + 1: min(len(lines), i + 5)]

        # Unit
        unit = ''
        for w in before + after:
            if _UNIT_LINE_RE.match(w):
                unit = w.lower()
                break

        # Flag (L = low, H = high)
        flag = ''
        for w in before + after:
            if _FLAG_LINE_RE.match(w):
                flag = w.upper()
                break

        # Numeric value: try AFTER first (row-by-row OCR), then BEFORE (column OCR)
        all_prefixes = {prefix for _, prefix in _KNOWN_LAB_PARAMS}
        value_str = None

        # 1. Scan lines AFTER param name (Toruń format, row-by-row)
        for w in after:
            wl_after = re.sub(r'\s*\(\d[,.\d]*\)\s*', '', w).strip().lower()
            if any(wl_after.startswith(pfx) for pfx in all_prefixes):
                break  # hit another param — stop
            if _FLAG_LINE_RE.match(w):  # skip flag lines
                continue
            if _UNIT_LINE_RE.match(w):  # skip unit lines
                continue
            if _NUM_LINE_RE.match(w):
                value_str = w
                break

        # 2. Fallback: scan BEFORE (Punkt Pobrań format, column OCR)
        if not value_str:
            for w in reversed(before):
                wl = re.sub(r'\s*\(\d[,.\d]*\)\s*', '', w).strip().lower()
                if any(wl.startswith(pfx) for pfx in all_prefixes):
                    break  # hit another param — don't steal its value
                if _FLAG_LINE_RE.match(w):  # skip misread flag ("11")
                    continue
                if _NUM_LINE_RE.match(w):
                    value_str = w
                    break
        if not value_str:
            continue

        # Build ↑/↓ indicator (handle both H/L and ↑/↓/& formats)
        indicator = ''
        param_lower = matched_display.lower()
        try:
            val = float(value_str.replace(',', '.'))
            if flag in ('L', '↓'):
                indicator = ' ↓'
                _generate_alert(param_lower, val, 'low', alerts)
            elif flag in ('H', '↑'):
                indicator = ' ↑'
                _generate_alert(param_lower, val, 'high', alerts)
            else:
                # Try to infer from min/max numbers in window
                ref_nums = [
                    float(w.replace(',', '.'))
                    for w in (before + after)
                    if _NUM_LINE_RE.match(w) and w != value_str
                ]
                if len(ref_nums) >= 2:
                    lo, hi = sorted(ref_nums[:2])
                    if val > hi:
                        indicator = ' ↑'
                        _generate_alert(param_lower, val, 'high', alerts)
                    elif val < lo:
                        indicator = ' ↓'
                        _generate_alert(param_lower, val, 'low', alerts)
        except (ValueError, TypeError):
            pass

        key = f"{matched_display} [{unit}]" if unit else matched_display
        fields[key] = value_str + indicator

    return fields, alerts


# ── IŁAWA MORPHOLOGY EXTRACTOR ────────────────────────────────────────────────
# Szpital Powiatowy Iława photos: Surya OCR merges each table column into one
# text block, so positional matching is impossible.  Strategy:
#   1. Extract ref ranges from the text and map them to known morphology params
#   2. Remove all ref-range numbers and metadata noise from text
#   3. Scan remaining decimal/integer values as candidates
#   4. For each param (ordered by range uniqueness), pick best candidate within
#      the param's known ref range ± 15%; fall back to OCR leading-digit
#      recovery ("8.9" → "38.9") if no direct match is found.

_ILAW_DETECT_RE = re.compile(r'WYNIK BADANIA LABORATORYJNEGO', re.I)

# Characterise ref ranges by their (lo, hi) bounds to identify which param
# they belong to.  Tuples: (param, lo_min, lo_max, hi_min, hi_max)
# Checked IN ORDER — first match wins — so put more-specific (narrow) entries first.
_REF_CHAR: list[tuple[str, float, float, float, float]] = [
    ("PCT",    0.10,  0.21,  0.28,  0.55),
    ("MCV",   70.0,  85.0,  87.0, 103.0),
    ("RDW-SD",35.5,  42.0,  42.0,  58.0),
    ("PLT",  120.0, 215.0, 270.0, 440.0),
    ("MCHC",  30.0,  33.5,  33.5,  38.5),
    ("MCH",   20.0,  27.9,  27.9,  38.5),
    # RDW-CV lo is typically 11-12 (NOT 9-10 which is PDW);
    # hi is typically 14-15 (NOT 15.7+ which is HGB)
    ("RDW-CV",10.5,  12.5,  12.0,  15.0),
    ("P-LCR", 10.0,  22.0,  35.0,  56.0),
    # PDW lo is typically 8-11 (lo_max 11.0 keeps HGB "11.2" out)
    ("PDW",    6.0,  11.0,  13.0,  22.0),
    ("MPV",    6.0,  10.2,   9.5,  14.5),
    ("HGB",   10.0,  13.0,  13.5,  18.5),
    ("HCT",   29.0,  38.5,  38.5,  55.0),
    ("WBC",    3.0,   4.5,   8.0,  13.0),
    ("RBC",    3.0,   4.6,   4.5,   6.5),
]

_REF_RANGE_EXTRACT_RE = re.compile(
    r'(?<!\d)(\d+[.,]?\d*)\s*[-–]\s*(\d+[.,]?\d*)(?!\d)'
)
_FLOAT_SCAN_RE = re.compile(r'(?<!\d)(\d{1,4}[.,]\d{1,4})(?!\d)')
_INT_SCAN_RE   = re.compile(r'(?<![.,\d])(\d{2,4})(?![.,\d])')


def _match_ref_to_param(lo: float, hi: float) -> str | None:
    if lo >= hi:
        return None
    for param, lo_min, lo_max, hi_min, hi_max in _REF_CHAR:
        if lo_min <= lo <= lo_max and hi_min <= hi <= hi_max:
            return param
    return None


def _extract_ilaw_morph_labs(text: str) -> tuple[dict, list[str]]:
    """Ref-range-anchored morphology extractor for Szpital Powiatowy Iława photos."""
    if not _ILAW_DETECT_RE.search(text):
        return {}, []
    tu = text.upper()
    if not any(p in tu for p in ('WBC', 'MORFOLOGIA', 'HGB', 'PLT')):
        return {}, []

    # ── Step 1: extract doc's own ref ranges and map to param names ───────────
    param_ref: dict[str, tuple[float, float]] = {}   # param → (ref_lo, ref_hi)
    for m in _REF_RANGE_EXTRACT_RE.finditer(text):
        lo_s = m.group(1).replace(',', '.')
        hi_s = m.group(2).replace(',', '.')
        try:
            lo, hi = float(lo_s), float(hi_s)
        except ValueError:
            continue
        p = _match_ref_to_param(lo, hi)
        if p and p not in param_ref:
            param_ref[p] = (lo, hi)

    # If we couldn't identify at least 5 params from ref ranges, bail out
    if len(param_ref) < 5:
        return {}, []

    # ── Step 2: remove ref range numbers and metadata from text ──────────────
    clean = text
    # Remove all X - Y range substrings (this eliminates ref-range numbers)
    clean = _REF_RANGE_EXTRACT_RE.sub(' REF ', clean)
    # Remove phone numbers like "(89) 644 97 04"
    clean = re.sub(r'\(?\d{2,3}\)?\s*\d{3}[\s\-]\d{2}[\s\-]\d{2}', ' TEL ', clean)
    # Remove ISO / Polish dates
    clean = re.sub(r'\d{4}-\d{2}-\d{2}', ' DATE ', clean)
    clean = re.sub(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}', ' DATE ', clean)
    # Remove IDs longer than 4 digits (PESEL, nr lab, zip+city codes)
    clean = re.sub(r'\b\d{5,}\b', ' ID ', clean)

    # ── Step 3: collect candidate decimal and integer values ──────────────────
    dec_vals: list[tuple[float, str]] = []
    for m in _FLOAT_SCAN_RE.finditer(clean):
        raw = m.group(1)
        try:
            dec_vals.append((float(raw.replace(',', '.')), raw))
        except ValueError:
            pass

    int_vals: list[tuple[float, str]] = []
    for m in _INT_SCAN_RE.finditer(clean):
        raw = m.group(1)
        n = int(raw)
        if 1900 <= n <= 2099:        # year token
            continue
        int_vals.append((float(n), raw))

    # ── Step 4: assign values to params ──────────────────────────────────────
    assigned: set[str] = set()
    fields: dict[str, str] = {}
    alerts: list[str] = []

    def _flag(v: float, lo: float, hi: float) -> str:
        if v < lo:
            return ' ↓'
        if v > hi:
            return ' ↑'
        return ''

    def _assign(param: str, v: float, raw: str, ref_lo: float, ref_hi: float,
                recovered: bool = False) -> None:
        display = (f"{v:.1f}" if recovered else raw.replace(',', '.'))
        fields[param] = display + _flag(v, ref_lo, ref_hi)
        assigned.add(raw)
        if param == 'HGB' and v < 11.5:
            alerts.append('anemia')
        if param == 'WBC' and v > 11.0:
            alerts.append('leukocytoza')
        if param == 'PLT' and v < 100:
            alerts.append('małopłytkowość')

    # Process params in order of range uniqueness (most specific first).
    # HCT BEFORE WBC: value "8.9" (OCR-truncated 38.9) would be grabbed by WBC
    # (range 3.98-10.04) unless HCT processes it first via leading-digit recovery.
    order = [
        "PCT", "MCV", "RDW-SD", "PLT",   # unique range, no overlap
        "MCHC", "MCH", "RDW-CV",          # somewhat unique
        "P-LCR", "PDW", "MPV",            # slightly overlapping
        "HCT", "WBC", "RBC",              # HCT first (marks "8.9" as assigned), then WBC/RBC claim direct values
        "HGB",                            # last: only "2.5" remains → OCR-recover to "12.5"
    ]
    for param in order:
        if param not in param_ref:
            continue
        ref_lo, ref_hi = param_ref[param]
        tol = max(1.0, (ref_hi - ref_lo) * 0.15)  # 15% tolerance

        pool = int_vals if param == "PLT" else dec_vals
        candidates = [
            (v, r) for v, r in pool
            if (ref_lo - tol) <= v <= (ref_hi + tol) and r not in assigned
        ]

        if candidates:
            mid = (ref_lo + ref_hi) / 2
            best_v, best_r = min(candidates, key=lambda x: abs(x[0] - mid))
            _assign(param, best_v, best_r, ref_lo, ref_hi)
            continue

        # OCR leading-digit recovery: "8.9" → "38.9" for HCT
        # Use EXACT norm range (no tolerance) to avoid false recoveries like
        # "2.5" → "32.5" which is barely inside the tolerance but wrong param.
        best_recovery: tuple | None = None
        best_dist = float('inf')
        mid = (ref_lo + ref_hi) / 2
        for v, raw in dec_vals:
            if raw in assigned or v >= ref_lo:
                continue
            for prefix in ('1', '2', '3', '4'):
                try:
                    restored = float(prefix + raw.replace(',', '.'))
                except ValueError:
                    continue
                if ref_lo <= restored <= ref_hi:
                    dist = abs(restored - mid)
                    if dist < best_dist:
                        best_dist = dist
                        best_recovery = (restored, raw)
                    break  # found in-norm recovery for this raw value; try next raw
        if best_recovery:
            _assign(param, best_recovery[0], best_recovery[1], ref_lo, ref_hi, recovered=True)

    return fields, alerts


# ── SPECIFIC TYPE PARSERS ─────────────────────────────────────────────────────

_MORPH_PARAMS = {
    # After layout reconstruction, rows look like: "WBC ........ 4.17   x 10^3/uL   3.98 - 10.04"
    # [\s.]{1,20} handles both "WBC: 4.17" (digital) and "WBC ........ 4.17" (photo/reconstructed)
    "HGB":    r"HGB[\s.:]{1,20}(\d+[.,]\d+)",
    "WBC":    r"WBC[\s.:]{1,20}(\d+[.,]\d+)",
    "RBC":    r"RBC[\s.:]{1,20}(\d+[.,]\d+)",
    "PLT":    r"PLT[\s.:]{1,20}(\d{2,4}[.,]?\d*)\b",
    "HCT":    r"HCT[\s.:]{1,20}(\d{2,3}[.,]\d+)",
    "MCV":    r"MCV[\s.:]{1,20}(\d{2,3}[.,]\d+)",
    "MCH":    r"\bMCH(?!C)[\s.:]{1,20}(\d{2,3}[.,]\d+)",
    "MCHC":   r"MCHC[\s.:]{1,20}(\d{2,3}[.,]\d+)",
    "RDW-SD": r"RDW-SD[\s.:]{1,20}(\d{2,3}[.,]\d+)",
    "RDW-CV": r"RDW-CV[\s.:]{1,20}(\d{2}[.,]\d+)",
    "PDW":    r"PDW[\s.:]{1,20}(\d+[.,]\d+)",
    "MPV":    r"MPV[\s.:]{1,20}(\d+[.,]\d+)",
    "P-LCR":  r"P-LCR[\s.:]{1,20}(\d{2,3}[.,]\d+)",
    "PCT":    r"PCT[\s.:]{1,20}(0[.,]\d{2,4})",
}

_MORPH_NORMS = {
    "HGB":    (11.5, 16.5),
    "WBC":    (4.0,  10.0),
    "RBC":    (3.5,  5.5),
    "PLT":    (150,  400),
    "HCT":    (35.0, 47.0),
    "MCV":    (79.0, 95.0),
    "MCH":    (25.0, 34.0),
    "MCHC":   (32.0, 36.0),
    "RDW-SD": (36.0, 47.0),
    "RDW-CV": (11.5, 14.5),
    "PDW":    (9.0,  17.0),
    "MPV":    (7.5,  12.5),
    "P-LCR":  (13.0, 43.0),
    "PCT":    (0.15, 0.40),
}


def _parse_morphology(text: str) -> tuple[dict, list[str]]:
    # Szpital Powiatowy Iława photos: column-scrambled OCR → range-based extractor
    fields, alerts = _extract_ilaw_morph_labs(text)
    if fields:
        return fields, alerts

    fields = {}
    alerts = []
    text_upper = text.upper()

    for param, pattern in _MORPH_PARAMS.items():
        m = re.search(pattern, text_upper, re.I)
        if m:
            val_str = m.group(1).replace(",", ".")
            try:
                val = float(val_str)
                if param in _MORPH_NORMS:
                    lo, hi = _MORPH_NORMS[param]
                    if val < lo:
                        fields[param] = f"{val_str} ↓"
                        if param == "HGB" and val < 11.5:
                            alerts.append(ScanAlert.anemia.value)
                        elif param == "PLT" and val < 100:
                            alerts.append(ScanAlert.trombocytopenia.value if hasattr(ScanAlert, 'trombocytopenia') else "małopłytkowość")
                    elif val > hi:
                        fields[param] = f"{val_str} ↑"
                        if param == "WBC" and val > 11.0:
                            alerts.append(ScanAlert.leukocytoza.value)
                    else:
                        fields[param] = val_str
                else:
                    fields[param] = val_str
            except ValueError:
                pass

    return fields, alerts


_LAB_PARAMS = {
    "Glukoza": r"glukoza[:\s]+(\d+[.,]\d*)\s*(?:mg/dL|mmol)?",
    "Kreatynina": r"kreatynina[:\s]+(\d+[.,]\d+)\s*(?:mg/dL|μmol)?",
    "Cholesterol": r"cholesterol[:\s]+(\d+[.,]\d*)\s*(?:mg/dL|mmol)?",
    "TSH": r"TSH[:\s]+(\d+[.,]\d+)\s*(?:μIU/mL|mIU/L)?",
    "FT4": r"FT4[:\s]+(\d+[.,]\d+)\s*(?:pmol/L|ng/dL)?",
    "ALT": r"ALT[:\s]+(\d+[.,]?\d*)\s*(?:U/L|IU/L)?",
    "AST": r"AST[:\s]+(\d+[.,]?\d*)\s*(?:U/L|IU/L)?",
    "GGTP": r"GGT[P]?[:\s]+(\d+[.,]?\d*)\s*(?:U/L|IU/L)?",
}


def _parse_lab(text: str) -> tuple[dict, list[str]]:
    # 1. ALAB "Sprawozdanie z badań laboratoryjnych" (pdftotext digital PDF)
    fields, alerts = _extract_alab_labs(text)
    if fields:
        return fields, alerts

    # 2. Lublin "Laboratorium Diagnostyczne" (pdftotext digital PDF)
    fields, alerts = _extract_lublin_labs(text)
    if fields:
        return fields, alerts

    # 3. Szpital Toruń row format (Param  Value  Range  Unit  ↑↓&) — Surya OCR
    fields, alerts = _extract_szpital_labs(text)
    if fields:
        return fields, alerts

    # 4. OPTIMed table format (min:X max:Y^) — Surya OCR
    fields, alerts = _extract_optimed_labs(text)
    if fields:
        return fields, alerts

    # 5. Context-based extractor for column-scrambled Surya OCR output
    fields, alerts = _extract_tabular_labs(text)
    if fields:
        return fields, alerts

    fields = {}
    alerts = []
    for param, pattern in _LAB_PARAMS.items():
        m = re.search(pattern, text, re.I)
        if m:
            val_str = m.group(1).replace(",", ".")
            fields[param] = val_str
            try:
                val = float(val_str)
                if param == "Glukoza" and val > 126:
                    alerts.append(ScanAlert.hiperglikemia.value)
                elif param == "Glukoza" and val < 70:
                    alerts.append(ScanAlert.hipoglikemia.value)
                elif param == "TSH" and val > 4.5:
                    alerts.append(ScanAlert.niedoczynnosc_tarczycy.value)
                elif param == "TSH" and val < 0.4:
                    alerts.append(ScanAlert.nadczynnosc_tarczycy.value)
            except ValueError:
                pass
    return fields, alerts


def _parse_recepta(text: str) -> tuple[dict, list[str]]:
    fields = {}
    drugs = re.findall(r"(?:Rp\.|lek[:\s]+)([^\n]{5,50})", text, re.I)
    if drugs:
        fields["leki"] = [d.strip() for d in drugs[:5]]
    refund = re.search(r"refundacja[:\s]+([^\n]{1,20})", text, re.I)
    if refund:
        fields["refundacja"] = refund.group(1).strip()
    return fields, []


def _parse_karta_informacyjna(text: str) -> tuple[dict, list[str]]:
    fields: dict = {}
    alerts: list[str] = []
    text_lower = text.lower()

    # 1. Diagnoses block
    rozp = re.search(
        r"rozpoznanie[^:\n]*[:\n]\s*(.*?)(?=\nzabiegi|\nleczenie|\nzalecenia|\nepikryza|\n\n\n)",
        text, re.I | re.S
    )
    if rozp:
        lines = [l.strip() for l in rozp.group(1).splitlines() if l.strip() and len(l.strip()) > 4]
        if lines:
            fields["rozpoznania"] = lines[:8]

    # 2. Admission / discharge dates
    m = re.search(r"data przyjęcia[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", text, re.I)
    if m:
        fields["data_przyjecia"] = m.group(1)

    m = re.search(r"data wypisu[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})", text, re.I)
    if m:
        fields["data_wypisu"] = m.group(1)

    # 3. Sick leave
    m = re.search(
        r"zwolnienie od[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s+do[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})",
        text, re.I
    )
    if m:
        fields["zwolnienie"] = f"{m.group(1)} – {m.group(2)}"

    # 4. Medications
    leki_block = re.search(
        r"leki przepisane\s*\n(.*?)(?=\n\n|\nbadania|\nbada|\nzalecenia|\nEOF|$)",
        text, re.I | re.S
    )
    if leki_block:
        raw_lines = [l.strip() for l in leki_block.group(1).splitlines() if l.strip()]
        med_kw = re.compile(r"\d+\s*mg|op\.|tabl|szt\.|kaps|inj\.|roztwór|zawiesina", re.I)
        meds = [l for l in raw_lines if med_kw.search(l)] or raw_lines
        if meds:
            fields["leki"] = meds[:8]
    else:
        farm = re.search(r"leczenie farmakologiczne\s*\n([^\n]+)", text, re.I)
        if farm:
            fields["leki"] = [s.strip() for s in re.split(r"[,;]", farm.group(1)) if s.strip()]

    # 5. Procedures (ICD-9 format)
    procs = re.findall(r"\(\d{2}\.\d+\)\s+([^\n]{10,90})", text)
    if procs:
        fields["zabiegi"] = [p.strip() for p in procs[:6]]

    # 6. Universal OPTIMed table extraction — gets ALL lab values
    lab_fields, lab_alerts = _extract_optimed_labs(text)
    fields.update(lab_fields)
    alerts.extend(lab_alerts)

    # 7. Keyword-based clinical alerts from diagnoses text
    if "nadciśnienie" in text_lower or "nadcisnienie" in text_lower:
        if "nadcisnienie" not in alerts:
            alerts.append("nadcisnienie")
    if "glikemia na czczo" in text_lower or "hiperglikemia" in text_lower:
        if "hiperglikemia" not in alerts:
            alerts.append("hiperglikemia")
    if "zawał" in text_lower or "infarct" in text_lower:
        if "pilne" not in alerts:
            alerts.append("pilne")

    return fields, alerts


# ── MAIN DISPATCH ─────────────────────────────────────────────────────────────

def parse_document(text: str, doc_type: DocType) -> tuple[dict, list[str], float]:
    common = _extract_common(text)
    fields = {}
    alerts = []

    if doc_type == DocType.morfologia:
        fields, alerts = _parse_morphology(text)
    elif doc_type == DocType.wynik_laboratoryjny:
        fields, alerts = _parse_lab(text)
    elif doc_type == DocType.recepta:
        fields, alerts = _parse_recepta(text)
    elif doc_type in (DocType.karta_informacyjna, DocType.epikryza):
        fields, alerts = _parse_karta_informacyjna(text)

    if "pilne" in text.lower() or "urgent" in text.lower():
        if "pilne" not in alerts:
            alerts.append("pilne")

    # Confidence based on number of extracted fields
    fields_conf = min(0.99, 0.60 + len(fields) * 0.02)
    return {**common, **fields}, list(set(alerts)), round(fields_conf, 2)
