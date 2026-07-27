import re
from schemas import DocType

_RULES: list[tuple[DocType, list[str], int]] = [
    # (doc_type, keywords, weight_multiplier)
    # Weight 3 = very specific document-level phrases that rarely appear elsewhere
    (DocType.karta_informacyjna, [
        "karta informacyjna z leczenia szpitalnego", "karta informacyjna",
        "rozpoznanie przy wypisie", "data wypisu", "data przyjęcia",
        "zalecenia", "leki przepisane", "leczenie farmakologiczne",
        "zabiegi / procedury", "epikryza",
    ], 3),
    (DocType.epikryza, [
        "epikryza", "karta wypisowa", "wypisany", "hospitalizacja",
        "przebieg kliniczny", "leczenie szpitalne", "rozpoznanie końcowe",
    ], 3),
    (DocType.morfologia, [
        "morfologia", "hgb", "wbc", "rbc", "plt", "hct", "mch", "mchc", "mpv",
        "hemoglobin", "leukocyt", "erytrocyt", "płytk",
    ], 1),
    (DocType.ekg, [
        "ekg", "elektrokardiogram", "rytm zatokowy", "qrs", "p-r", "st odcinek",
        "kardiogram", "holter",
    ], 1),
    (DocType.recepta, [
        "rp.", "recepta", "przepisał", "lek:", "dawkowanie", "op.", "mg/", "tabl.",
        "tabletki", "krople", "maść", "refundacja",
    ], 1),
    (DocType.skierowanie, [
        "skierowanie", "proszę o konsultację", "proszę o przyjęcie",
        "diagnoza wstępna", "skierowuję",
    ], 1),
    (DocType.rtg_usg, [
        "rtg", "usg", "tomografia", "rezonans", "mr ", "ct ", "zdjęcie rtg",
        "ultrasonografia", "badanie obrazowe", "opisuję:", "opis badania",
    ], 1),
    (DocType.wynik_laboratoryjny, [
        # wysokowagowe frazy tytułowe
        "wyniki badań laboratoryjnych", "wynik laboratoryjny", "wyniki laboratoryjne",
        "sprawozdanie z badań laboratoryjnych", "sprawozdanie z badania",
        "wynik badania laboratoryjnego",
        "zakład diagnostyki laboratoryjnej", "pracownia diagnostyki",
        "laboratorium diagnostyczne", "alab laboratoria",
        # parametry biochemiczne i ogólne
        "wynik", "laboratorium", "norma", "zakres ref", "j. miary", "zakres referencyjny",
        "glukoza", "kreatynina", "cholesterol", "tsh", "ft4", "ft3",
        "bilirubina", "ast", "alt", "ggtp", "albumin", "mocz",
        "crp", "asp", "aptt", "trójgliceryd", "kwas moczowy",
        "estradiol", "tyreotropina", "tyroksyna",
    ], 1),
]


def classify(text: str) -> tuple[DocType, float]:
    text_lower = text.lower()
    scores: dict[DocType, float] = {}

    for doc_type, keywords, weight in _RULES:
        hit = sum(1 for kw in keywords if kw in text_lower)
        if hit:
            scores[doc_type] = hit * weight

    if not scores:
        return DocType.inny, 0.5

    best = max(scores, key=lambda k: scores[k])
    total_keywords = next(len(kws) for dt, kws, _ in _RULES if dt == best)
    raw_hits = scores[best] / next(w for dt, _, w in _RULES if dt == best)
    confidence = min(0.99, 0.55 + (raw_hits / total_keywords) * 0.44)
    return best, round(confidence, 2)


DOC_TYPE_LABELS = {
    DocType.morfologia: "Morfologia krwi",
    DocType.ekg: "EKG",
    DocType.recepta: "Recepta",
    DocType.skierowanie: "Skierowanie",
    DocType.epikryza: "Epikryza",
    DocType.karta_informacyjna: "Karta informacyjna leczenia szpitalnego",
    DocType.rtg_usg: "Badanie obrazowe (RTG/USG/TK/MR)",
    DocType.wynik_laboratoryjny: "Wynik laboratoryjny",
    DocType.inny: "Dokument medyczny",
}
