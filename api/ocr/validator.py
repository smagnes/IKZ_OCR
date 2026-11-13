"""
Walidator wyników OCR — anti-hallucination layer.

Nie używamy AI do weryfikacji AI. Używamy deterministycznych reguł:
- biologiczne granice wartości (niemożliwe fizjologicznie = błąd OCR)
- spójność jednostki z parametrem
- spójność wartości z zakresem referencyjnym z dokumentu
"""
from __future__ import annotations
import re
from typing import Optional

# ── Biologiczne granice per parametr ──────────────────────────────────────────
# Format: (min, max, expected_unit_keywords)
# Wartość poza zakresem = prawie na pewno błąd OCR (zgubiona kropka, zamienione cyfry)
_PLAUSIBILITY: dict[str, tuple[float, float, list[str]]] = {
    # Lipidogram
    "cholesterol":        (10.0,  1000.0,  ["mg/dl", "mg/dL", "mmol/l", "mmol/L"]),
    "hdl":                (1.0,   200.0,   ["mg/dl", "mg/dL", "mmol/l"]),
    "ldl":                (1.0,   600.0,   ["mg/dl", "mg/dL", "mmol/l"]),
    "trójglicerydy":      (5.0,   3000.0,  ["mg/dl", "mg/dL", "mmol/l"]),
    "triglicerydy":       (5.0,   3000.0,  ["mg/dl", "mg/dL", "mmol/l"]),
    # Glukoza
    "glukoza":            (10.0,  3000.0,  ["mg/dl", "mg/dL", "mmol/l"]),
    "hba1c":              (3.0,   20.0,    ["%"]),
    # Tarczyca
    "tsh":                (0.001, 200.0,   ["miu/l", "µiu/ml", "uiu/ml", "miu/ml"]),
    "ft3":                (0.1,   50.0,    ["pg/ml", "pmol/l"]),
    "ft4":                (0.01,  10.0,    ["ng/dl", "pmol/l"]),
    # Morfologia
    "hemoglobina":        (1.0,   25.0,    ["g/dl"]),
    "hematokryt":         (5.0,   70.0,    ["%"]),
    "erytrocyty":         (0.5,   10.0,    ["mln/ul", "10*6/ul", "t/l"]),
    "leukocyty":          (0.1,   200.0,   ["tys/ul", "10*3/ul", "g/l"]),
    "trombocyty":         (5.0,   2000.0,  ["tys/ul", "10*3/ul"]),
    "płytki krwi":        (5.0,   2000.0,  ["tys/ul", "10*3/ul"]),
    "mcv":                (50.0,  130.0,   ["fl"]),
    "mch":                (10.0,  50.0,    ["pg"]),
    "mchc":               (20.0,  45.0,    ["g/dl"]),
    # Nerki
    "kreatynina":         (0.1,   50.0,    ["mg/dl", "µmol/l", "umol/l"]),
    "mocznik":            (1.0,   400.0,   ["mg/dl", "mmol/l"]),
    "kwas moczowy":       (0.5,   30.0,    ["mg/dl", "µmol/l"]),
    "egfr":               (1.0,   200.0,   ["ml/min", "ml/min/{1.73_m2}"]),
    # Wątroba
    "alt":                (1.0,   5000.0,  ["u/l", "iu/l"]),
    "ast":                (1.0,   5000.0,  ["u/l", "iu/l"]),
    "ggtp":               (1.0,   5000.0,  ["u/l", "iu/l"]),
    "alp":                (1.0,   3000.0,  ["u/l", "iu/l"]),
    "bilirubina":         (0.1,   100.0,   ["mg/dl", "µmol/l"]),
    # Stan zapalny
    "crp":                (0.01,  1000.0,  ["mg/l", "mg/dl"]),
    # Tarczyca — dodatkowe
    "ferrytyna":          (0.1,   50000.0, ["ng/ml", "µg/l", "pmol/l"]),
    "witamina d":         (1.0,   300.0,   ["ng/ml", "nmol/l", "µg/l"]),
    "witamina b12":       (10.0,  10000.0, ["pg/ml", "pmol/l"]),
    # Sód / potas
    "sód":                (100.0, 180.0,   ["mmol/l", "meq/l"]),
    "potas":              (1.0,   10.0,    ["mmol/l", "meq/l"]),
}

# ── Znane złe jednostki dla parametrów ────────────────────────────────────────
# Jeśli jednostka jest z tej listy dla danego parametru → prawdopodobny błąd OCR
_UNIT_MISMATCH: dict[str, list[str]] = {
    "tsh":       ["mg/dl", "g/dl", "mmol/l"],   # TSH nigdy nie jest w mg/dl
    "hemoglobina": ["miu/ml", "iu/l"],
    "sód":       ["mg/dl"],
    "potas":     ["mg/dl"],
}


def _normalize_name(name: str) -> str:
    return name.lower().strip().rstrip('.:')


def _normalize_unit(unit: str) -> str:
    return unit.lower().strip() if unit else ""


def validate_result(
    name: str,
    value_str: str,
    unit: str,
    ref_low: Optional[float] = None,
    ref_high: Optional[float] = None,
) -> tuple[float, list[str]]:
    """
    Zwraca (confidence: 0.0-1.0, reasons: list[str]).

    confidence < 0.85 → needs_review = true w JSON.
    confidence < 0.5  → prawdopodobny błąd OCR, wartość podejrzana.
    """
    score = 1.0
    reasons: list[str] = []

    # Parsuj wartość
    try:
        value = float(value_str.replace(',', '.'))
    except (ValueError, AttributeError):
        return 0.3, ["unparseable_value"]

    norm_name = _normalize_name(name)
    norm_unit = _normalize_unit(unit)

    # ── 1. Spójność jednostki z parametrem ────────────────────────────────────
    for key, (lo, hi, expected_units) in _PLAUSIBILITY.items():
        if key in norm_name:
            # Sprawdź czy jednostka jest z listy oczekiwanych
            unit_ok = any(eu in norm_unit for eu in expected_units)
            if norm_unit and not unit_ok:
                # Sprawdź czy to znana zła jednostka
                bad_units = _UNIT_MISMATCH.get(key, [])
                if any(bu in norm_unit for bu in bad_units):
                    score -= 0.5
                    reasons.append("unit_mismatch")
                else:
                    score -= 0.15
                    reasons.append("unit_unexpected")
            break

    # ── 2. Biologiczna plausybilność ──────────────────────────────────────────
    for key, (lo, hi, expected_units) in _PLAUSIBILITY.items():
        if key in norm_name:
            if value < lo or value > hi:
                score -= 0.6
                reasons.append("value_out_of_biological_range")
            # Dodatkowy check: czy wartość mieści się w oczekiwanej jednostce
            # np. glukoza 1230 mg/dL = biologicznie niemożliwe
            elif norm_unit and any(eu in norm_unit for eu in expected_units):
                # Wartość jest w "dobrej" jednostce ale 10x poza zakresem plausibility
                if value > hi * 5:
                    score -= 0.5
                    reasons.append("value_out_of_biological_range")
            break

    # ── 3. Spójność z zakresem referencyjnym z dokumentu ─────────────────────
    if ref_low is not None or ref_high is not None:
        ref_center = None
        if ref_low is not None and ref_high is not None:
            ref_center = (ref_low + ref_high) / 2
        elif ref_high is not None:
            ref_center = ref_high
        elif ref_low is not None:
            ref_center = ref_low

        if ref_center and ref_center > 0:
            ratio = value / ref_center
            # Wartość 20x powyżej lub 50x poniżej centrum zakresu
            # (asymetria: wartości bardzo wysokie częściej błąd niż bardzo niskie)
            if ratio > 20 or ratio < 0.02:
                score -= 0.45
                reasons.append("value_order_of_magnitude_vs_reference")

        # Wartość > 10x powyżej górnej granicy zakresu → zawsze needs_review
        if ref_high and ref_high > 0 and value > ref_high * 10:
            score = min(score, 0.84)   # wymusza needs_review ale nie jest błędem
            if "value_order_of_magnitude_vs_reference" not in reasons:
                reasons.append("value_far_above_reference")

    # ── 4. Podejrzane wzorce OCR ──────────────────────────────────────────────
    # Wartości będące okrągłymi potęgami 10 mogą być błędem (1000, 10000)
    if value > 0 and value == int(value):
        v = int(value)
        if v in (1000, 10000, 100000) and norm_unit not in ["tys/ul", "10*3/ul"]:
            score -= 0.2
            reasons.append("suspiciously_round_value")

    return round(max(0.0, min(1.0, score)), 2), reasons


def needs_review(confidence: float) -> bool:
    return confidence < 0.85
