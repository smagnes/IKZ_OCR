# IKZOCR — Dokumentacja developerska

## Architektura

```
ikzocr/
├── api/                    # FastAPI backend (Python 3.12)
│   ├── main.py             # Endpointy HTTP, middleware, auth
│   ├── db.py               # Zapytania PostgreSQL (asyncpg)
│   ├── schemas.py          # Modele Pydantic
│   ├── settings.py         # Konfiguracja (env vars)
│   └── ocr/
│       ├── processor.py    # Surya OCR wrapper, layout reconstruction
│       ├── classifier.py   # Wykrywanie typu dokumentu (regex scoring)
│       └── parser.py       # Ekstrakcja danych (PESEL, parametry lab, leki...)
├── panel/                  # Next.js 14 frontend (TypeScript)
│   └── src/
│       ├── app/            # App Router (scan, documents, statistics, api-keys)
│       ├── components/     # MedicalResultView, shared UI
│       └── lib/
│           ├── api.ts      # Klient API (fetch + typy)
│           └── auth.ts     # JWT auth helpers
├── docs/                   # Dokumentacja
├── init.sql                # Schemat bazy danych
└── docker-compose.yml
```

## Środowisko deweloperskie

### Wymagania
- Python 3.12+
- Node.js 20+
- Docker (do PostgreSQL i Redis)
- Git

### Setup API (backend)

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Uruchom zależności (tylko DB i Redis)
docker compose up -d db redis

# Zmienne środowiskowe
cp .env.example .env

# Uruchom API (dev mode)
uvicorn main:app --reload --port 8000
```

### Setup Panel (frontend)

```bash
cd panel
npm install

# Zmienne środowiskowe
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
echo "NEXT_PUBLIC_API_KEY=mk_cvECCJSJ_p0HNZoRv1N6365y66c" >> .env.local

# Uruchom panel (dev mode)
npm run dev
```

## Komponenty OCR

### Processor (`api/ocr/processor.py`)

Odpowiada za wczytanie pliku i uruchomienie OCR:

1. **PDF cyfrowy** → `pdftotext -layout` (szybki, dokładny)
2. **Zdjęcie / skan PDF** → Surya OCR → `_reconstruct_layout()` (rekonstrukcja kolejności bloków)

`_reconstruct_layout()` sortuje bloki tekstu po współrzędnych Y/X, wstawiając spacje proporcjonalne do odległości między blokami. Surya często zwraca kolumny w odwrotnej kolejności — ta funkcja przywraca porządek czytania.

### Classifier (`api/ocr/classifier.py`)

Scoring słów kluczowych z wagami. Typ dokumentu = kategoria z najwyższym score. Pewność = proporcja trafionych słów kluczowych.

### Parser (`api/ocr/parser.py`)

Ekstrakcja danych ze znormalizowanego tekstu OCR. Kluczowe mechanizmy:

**Morfologia (dokumenty fotografowane):**
- `_extract_ilaw_morph_labs()` — ekstraktor oparty na zakresach referencyjnych
- Zamiast szukać `HGB: 12.5` (które Surya łączy w osobne kolumny), wyciąga zakresy ref z dokumentu (`11.2 - 15.7`), mapuje je na parametry via `_REF_CHAR`, a następnie przypisuje wartości z cleaned textu
- OCR recovery: `"2.5"` → próbuje prefiksy `1,2,3,4` → `"12.5"` mieści się w zakresie HGB ✓

**PESEL:**
- Wzorzec z etykietą: `PESEL: 12345678901`
- Wzorzec odwrócony (Surya zwraca kolumny): `12345678901\nPESEL`
- Wzorzec bare: walidacja cyfry kontrolnej + data urodzenia w pierwszych 6 cyfrach

## Schemat bazy danych

Główne tabele (patrz `init.sql`):

```sql
api_keys   -- klucze API, plany, limity
users      -- konta użytkowników (JWT auth)
scans      -- wyniki OCR (JSONB dla fields i alerts)
```

Kolumna `fields` i `alerts` to JSONB — możliwe zapytania po zawartości:
```sql
SELECT * FROM scans WHERE fields->>'HGB' IS NOT NULL;
SELECT * FROM scans WHERE 'anemia' = ANY(SELECT jsonb_array_elements_text(alerts));
```

## Dodawanie nowego typu dokumentu

1. **Dodaj enum** w `schemas.py`:
```python
class DocType(str, Enum):
    nowy_typ = "nowy_typ"
```

2. **Dodaj słowa kluczowe** w `classifier.py`:
```python
(DocType.nowy_typ, ["słowo1", "słowo2"], 1),
```

3. **Dodaj etykietę** w `classifier.py`:
```python
DOC_TYPE_LABELS = {
    DocType.nowy_typ: "Opis wyświetlany",
}
```

4. **Dodaj parser** w `parser.py` — funkcja `_parse_nowy_typ(text) -> tuple[dict, list[str]]`

5. **Podepnij** w `parse_document()`:
```python
elif doc_type == DocType.nowy_typ:
    fields, alerts = _parse_nowy_typ(text)
```

## Dodawanie parametru do morfologii

W `parser.py`:

1. Dodaj wzorzec do `_MORPH_PARAMS`:
```python
"NOWY_PARAM": r"NOWY_PARAM[\s.:]{1,20}(\d+[.,]\d+)",
```

2. Dodaj zakresy normalne do `_MORPH_NORMS`:
```python
"NOWY_PARAM": (dolna_norma, gorna_norma),
```

3. Dodaj charakterystykę zakresu referencyjnego do `_REF_CHAR`:
```python
("NOWY_PARAM", lo_min, lo_max, hi_min, hi_max),
```

4. Dodaj do listy `order` w `_extract_ilaw_morph_labs()`.

## Zmienne środowiskowe

| Zmienna | Wymagana | Opis |
|---------|----------|------|
| `DATABASE_URL` | ✓ | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | ✓ | JWT secret (min. 32 znaki) |
| `POSTGRES_*` | ✓ | Dane do bazy |
| `SMTP_HOST` | — | Email (wysyłka wyników) |
| `SMTP_PORT` | — | Domyślnie 587 |
| `SMTP_USER` | — | Login SMTP |
| `SMTP_PASS` | — | Hasło SMTP |
| `EMAIL_FROM` | — | Adres nadawcy |
| `ENVIRONMENT` | — | `development` / `production` |

## Testy

```bash
# Backend
cd api
pytest tests/ -v

# Manualny test OCR
curl -X POST http://localhost:8000/v1/scan \
  -H "Authorization: Bearer mk_cvECCJSJ_p0HNZoRv1N6365y66c" \
  -F "file=@tests/fixtures/morfologia.jpg"

# Frontend
cd panel
npm run type-check
npm run build
```
