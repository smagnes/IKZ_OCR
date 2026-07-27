# IKZOCR — Developer Guide

## Spis treści

1. [Wymagania i setup lokalny](#1-wymagania-i-setup-lokalny)
2. [Uruchomienie środowiska deweloperskiego](#2-uruchomienie-środowiska-deweloperskiego)
3. [Struktura projektu — szczegółowy opis](#3-struktura-projektu--szczegółowy-opis)
4. [Backend — FastAPI deep dive](#4-backend--fastapi-deep-dive)
5. [OCR Pipeline — jak to działa od środka](#5-ocr-pipeline--jak-to-działa-od-środka)
6. [Jak dodać nowy typ dokumentu](#6-jak-dodać-nowy-typ-dokumentu)
7. [Jak dodać nowy parametr laboratoryjny](#7-jak-dodać-nowy-parametr-laboratoryjny)
8. [Frontend — Next.js deep dive](#8-frontend--nextjs-deep-dive)
9. [Baza danych — migracje i schematy](#9-baza-danych--migracje-i-schematy)
10. [Testowanie](#10-testowanie)
11. [Zmienne środowiskowe](#11-zmienne-środowiskowe)
12. [Debugowanie typowych problemów](#12-debugowanie-typowych-problemów)
13. [Workflow CI/CD](#13-workflow-cicd)
14. [Konwencje kodu](#14-konwencje-kodu)

---

## 1. Wymagania i setup lokalny

### Wymagania systemowe

| Narzędzie | Minimalna wersja | Sprawdzenie |
|-----------|-----------------|-------------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Python | 3.11+ | `python3 --version` |
| Node.js | 20 LTS | `node --version` |
| npm | 10+ | `npm --version` |
| Git | 2.40+ | `git --version` |

Opcjonalnie (dev backend bez Dockera):
- `libmagic` — `apt install libmagic1` (Linux) / `brew install libmagic` (macOS)
- `poppler-utils` — do konwersji PDF: `apt install poppler-utils`

### Klonowanie i pierwsze uruchomienie

```bash
git clone https://github.com/smagnes/IKZ_OCR.git
cd IKZ_OCR

# Skopiuj konfigurację
cp api/.env.example api/.env

# Uruchom cały stack
docker compose up -d

# Sprawdź logi OCR API (pierwsze uruchomienie ściąga modele Surya ~1.5 GB)
docker compose logs -f ocr-api

# Poczekaj na komunikat:
# "Models loaded. Ready."
# (może trwać 2-5 minut przy pierwszym uruchomieniu)
```

Panel dostępny pod: `http://localhost:3000`  
API dostępne pod: `http://localhost:8000`  
Dokumentacja API (Swagger): `http://localhost:8000/docs`

---

## 2. Uruchomienie środowiska deweloperskiego

### 2.1 Backend (Python) — bez Dockera

Praca bezpośrednio z kodem Pythona (szybszy reload, łatwiejszy debugger):

```bash
cd api

# Utwórz virtualenv
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# Zainstaluj zależności
pip install -r requirements.txt

# Uruchom tylko postgres i redis przez Docker
docker compose up -d postgres redis

# Uruchom API z hot-reload
PRELOAD_MODELS=false \
DATABASE_URL=postgresql://medyk:medyk@localhost:5432/medykocr \
REDIS_URL=redis://localhost:6379 \
uvicorn main:app --reload --port 8000
```

`PRELOAD_MODELS=false` powoduje że modele Surya ładują się dopiero przy pierwszym żądaniu — restart jest wtedy natychmiastowy.

### 2.2 Frontend (Next.js) — bez Dockera

```bash
cd panel

# Zainstaluj zależności
npm install

# Ustaw URL backendu
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Uruchom dev server z hot-reload
npm run dev
# → dostępny pod http://localhost:3000
```

### 2.3 Przydatne komendy Docker Compose

```bash
# Status wszystkich kontenerów
docker compose ps

# Logi konkretnego serwisu
docker compose logs -f ocr-api
docker compose logs -f panel
docker compose logs -f postgres

# Restart konkretnego serwisu (po zmianie kodu)
docker compose restart ocr-api

# Rebuild obrazu po zmianie requirements.txt lub Dockerfile
docker compose build ocr-api
docker compose up -d ocr-api

# Shell wewnątrz kontenera
docker compose exec ocr-api bash
docker compose exec postgres psql -U medyk -d medykocr

# Wyczyść wszystko (UWAGA: usuwa volumes z danymi!)
docker compose down -v
```

### 2.4 Inicjalizacja bazy danych

Schemat jest aplikowany automatycznie przy pierwszym uruchomieniu przez `init.sql`. Jeśli chcesz zresetować bazę:

```bash
docker compose down postgres
docker volume rm ikzocr_postgres_data
docker compose up -d postgres
# Poczekaj ~5s na start PostgreSQL
docker compose restart ocr-api
```

### 2.5 Tworzenie testowego klucza API

```bash
# Przez panel: http://localhost:3000/api-keys → Nowy klucz

# Albo wstaw bezpośrednio do bazy (tylko dev!)
docker compose exec postgres psql -U medyk -d medykocr -c "
INSERT INTO organizations (name, plan, scan_limit)
VALUES ('Dev Org', 'enterprise', 99999);

INSERT INTO api_keys (org_id, key_hash, name, plan, daily_limit)
SELECT id,
       encode(sha256('mk_devkey_test123'::bytea), 'hex'),
       'dev-key',
       'enterprise',
       99999
FROM organizations WHERE name = 'Dev Org';
"
# Klucz: mk_devkey_test123
```

---

## 3. Struktura projektu — szczegółowy opis

```
IKZ_OCR/
│
├── api/                          # FastAPI backend
│   ├── main.py                   # Router, middleware, handlery endpointów
│   ├── db.py                     # Pool asyncpg, helper queries
│   ├── schemas.py                # Modele Pydantic (request/response)
│   ├── requirements.txt          # Zależności Python (pinned versions)
│   ├── Dockerfile                # Multi-stage build (builder + runtime)
│   ├── .env.example              # Szablon zmiennych środowiskowych
│   └── ocr/
│       ├── __init__.py
│       ├── processor.py          # Wrapper Surya: init modeli, przetwarzanie
│       ├── classifier.py         # Wykrywanie typu dokumentu
│       └── parser.py             # Ekstrakcja danych, alerty, PESEL
│
├── panel/                        # Next.js 14 frontend
│   ├── src/
│   │   ├── app/                  # App Router (Next.js 13+)
│   │   │   ├── layout.tsx        # Root layout z ConditionalLayout
│   │   │   ├── page.tsx          # Strona główna (redirect)
│   │   │   ├── login/page.tsx    # Logowanie
│   │   │   ├── register/page.tsx # Rejestracja
│   │   │   ├── scan/page.tsx     # Upload + wynik OCR
│   │   │   ├── documents/page.tsx# Historia skanów
│   │   │   ├── api-keys/page.tsx # Zarządzanie kluczami
│   │   │   ├── statistics/page.tsx
│   │   │   ├── facilities/page.tsx
│   │   │   └── plan/page.tsx
│   │   ├── components/
│   │   │   ├── MedicalResultView.tsx  # Główny komponent wyniku OCR
│   │   │   ├── Sidebar.tsx            # Nawigacja boczna
│   │   │   └── ConditionalLayout.tsx  # Ukrywa sidebar na /login i /register
│   │   └── lib/
│   │       ├── api.ts            # Klient HTTP + download helpers
│   │       └── auth.ts           # JWT helpers (getToken, isAuthenticated)
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── Dockerfile
│
├── docs/                         # Dokumentacja (ten katalog)
├── docs/legal/                   # Dokumenty prawne
├── monitoring/
│   ├── prometheus.yml            # Konfiguracja scrape targets
│   └── grafana/
│       └── provisioning/
│           └── datasources/
│               └── prometheus.yml
├── init.sql                      # Schemat bazy danych
├── docker-compose.yml            # Definicja całego stacku
├── .gitignore
├── CHANGELOG.md
├── LICENSE
└── README.md
```

---

## 4. Backend — FastAPI deep dive

### 4.1 main.py — architektura endpointów

```python
# Struktura main.py

from fastapi import FastAPI, Depends, File, UploadFile, Header, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
import asyncio, hashlib, io

app = FastAPI(title="IKZOCR API", version="0.3.0")

# ─── Auth dependency ──────────────────────────────────────────────────────────

async def verify_api_key(authorization: str = Header(...)) -> dict:
    """Weryfikuje Bearer token, zwraca wiersz z api_keys."""
    ...

# ─── Endpointy (KOLEJNOŚĆ WAŻNA: statyczne przed {param}) ────────────────────

@app.get("/health")
async def health(): ...

@app.post("/v1/auth/register")
async def register(): ...

@app.post("/v1/auth/login")
async def login(): ...

@app.post("/v1/scan")
async def scan_document(file: UploadFile, api_key = Depends(verify_api_key)): ...

@app.get("/v1/documents/export")          # ← statyczna PRZED /{scan_id}
async def export_all_csv(): ...

@app.get("/v1/documents/export.md")       # ← statyczna
async def export_all_md(): ...

@app.get("/v1/documents")
async def list_documents(): ...

@app.get("/v1/documents/{scan_id}")       # ← dynamiczna
async def get_document(): ...

@app.get("/v1/documents/{scan_id}/export.txt")
async def export_txt(): ...

@app.get("/v1/documents/{scan_id}/export.md")
async def export_md(): ...

@app.get("/v1/documents/{scan_id}/export.csv")
async def export_csv(): ...
```

### 4.2 db.py — warstwa danych

`db.py` zarządza pulą połączeń asyncpg i eksponuje pomocnicze funkcje.

```python
import asyncpg
import os

_pool: asyncpg.Pool | None = None

async def init_pool():
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=os.getenv("DATABASE_URL"),
        min_size=2,
        max_size=10,
        command_timeout=30
    )

async def fetchrow(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.fetchrow(query, *args)

async def fetch(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.fetch(query, *args)

async def execute(query: str, *args):
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)

async def save_scan(api_key_id: str, result: dict) -> str:
    """Zapisuje wynik OCR i zwraca scan_id."""
    import json, uuid
    scan_id = str(uuid.uuid4())
    await execute("""
        INSERT INTO scans (id, api_key_id, doc_type, raw_text, parsed_json, confidence)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6)
    """, scan_id, api_key_id,
        result.get("doc_type"),
        result.get("raw_text"),
        json.dumps(result.get("parsed_data", {})),
        result.get("confidence")
    )
    return scan_id
```

### 4.3 schemas.py — modele Pydantic

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ScanResponse(BaseModel):
    scan_id: str
    doc_type: Optional[str]
    confidence: Optional[float]
    parsed_data: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    raw_text: Optional[str]
    processing_time_ms: int

class DocumentListItem(BaseModel):
    id: str
    doc_type: Optional[str]
    confidence: Optional[float]
    file_name: Optional[str]
    created_at: datetime
    patient_name: Optional[str]
    exam_date: Optional[str]

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    daily_limit: int = Field(default=200, ge=1, le=10000)

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    org_name: str = Field(..., min_length=2)
```

### 4.4 Obsługa plików wejściowych i walidacja

```python
@app.post("/v1/scan")
async def scan_document(
    file: UploadFile = File(...),
    api_key: ApiKey = Depends(verify_api_key)
):
    content = await file.read()

    # Walidacja rozmiaru
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "Plik zbyt duży (max 20MB)")

    # Walidacja magic bytes (nie ufamy Content-Type klienta)
    mime = magic.from_buffer(content, mime=True)
    if mime not in ("image/jpeg", "image/png", "image/tiff", "application/pdf"):
        raise HTTPException(415, f"Nieobsługiwany format: {mime}")

    # PDF → pierwsza strona jako obraz
    if mime == "application/pdf":
        content = pdf_to_image(content)

    # Limit dzienny (Redis)
    count_key = f"scan_count:{api_key.id}:{date.today().isoformat()}"
    daily_count = await redis.incr(count_key)
    await redis.expire(count_key, 86400)
    if daily_count > api_key.daily_limit:
        raise HTTPException(429, "Dzienny limit skanów wyczerpany")

    # OCR — blokujące, wywołaj w osobnym wątku
    t0 = time.monotonic()
    result = await asyncio.to_thread(processor.process, content)
    processing_ms = int((time.monotonic() - t0) * 1000)

    scan_id = await db.save_scan(api_key.id, result)

    return {"scan_id": scan_id, "processing_time_ms": processing_ms, **result}
```

---

## 5. OCR Pipeline — jak to działa od środka

### 5.1 processor.py — inicjalizacja i przetwarzanie

Modele Surya (~1.5 GB) ładowane są raz przy starcie i trzymane w pamięci przez cały czas życia procesu.

```python
# api/ocr/processor.py
from surya.model.detection import segformer
from surya.model.recognition.model import load_model
from surya.model.recognition.processor import load_processor
from surya.detection import batch_text_detection
from surya.recognition import run_recognition
from PIL import Image, ImageOps
from io import BytesIO

_det_model = _det_processor = _rec_model = _rec_processor = None

def preload_models():
    global _det_model, _det_processor, _rec_model, _rec_processor
    _det_model, _det_processor = segformer.load_model(), segformer.load_processor()
    _rec_model = load_model()
    _rec_processor = load_processor()

def process(image_bytes: bytes) -> dict:
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img = ImageOps.exif_transpose(img)          # napraw orientację EXIF

    # Detekcja bboxów tekstu
    det = batch_text_detection([img], _det_model, _det_processor)

    # Rozpoznanie tekstu z wyciętych fragmentów
    rec = run_recognition(
        [img], [det[0].bboxes], _rec_model, _rec_processor, langs=[["pl", "en"]]
    )
    text_lines = rec[0].text_lines

    from .parser import _reconstruct_layout, parse
    from .classifier import classify

    raw_text = _reconstruct_layout(text_lines)
    doc_type  = classify(raw_text)
    parsed    = parse(doc_type, raw_text, text_lines)

    confidence = sum(tl.confidence for tl in text_lines) / max(len(text_lines), 1)

    return {
        "doc_type":    doc_type,
        "raw_text":    raw_text,
        "parsed_data": parsed,
        "alerts":      parsed.pop("alerts", []),
        "confidence":  round(confidence, 3),
    }
```

### 5.2 Rekonstrukcja układu strony — szczegóły

Problem: Surya skanuje tabelę laboratoryjną kolumnami (top-to-bottom per kolumna), a nie wierszami (left-to-right). Wynik jest nieczytelny bez rekonstrukcji.

```python
def _reconstruct_layout(text_lines, h_gap_threshold: float = 30.0) -> str:
    if not text_lines:
        return ""

    # Grupuj linie według Y (ten sam wiersz = Y1 różni się o max 8px)
    Y_TOL = 8.0
    rows = []
    for tl in sorted(text_lines, key=lambda t: t.bbox[1]):
        y1 = tl.bbox[1]
        placed = False
        for row in rows:
            if abs(row[0].bbox[1] - y1) <= Y_TOL:
                row.append(tl)
                placed = True
                break
        if not placed:
            rows.append([tl])

    lines_out = []
    for row in rows:
        row.sort(key=lambda t: t.bbox[0])   # sortuj po X w wierszu
        parts = []
        prev_x2 = None
        for tl in row:
            x1 = tl.bbox[0]
            if prev_x2 is not None:
                gap = x1 - prev_x2
                # Duża przerwa = granica kolumny → wstaw 2 spacje (ważne dla regex!)
                parts.append("  " if gap > h_gap_threshold else " " * max(1, int(gap / 10)))
            parts.append(tl.text)
            prev_x2 = tl.bbox[2]
        lines_out.append("".join(parts))

    return "\n".join(lines_out)
```

### 5.3 Ekstrakcja morfologii — algorytm ref-range

Każdy parametr morfologii identyfikowany jest przez swój unikalny zakres referencyjny (np. "12.0-16.0" → HGB). Wartość wynikowa to liczba znaleziona obok tego zakresu.

```python
# Kolejność przetwarzania — krytyczna dla uniknięcia kolizji!
# HCT PRZED WBC: wartość "8.9" (OCR: ucięty "38.9") mieści się w zakresie WBC [3.07, 11]
# HGB NA KOŃCU: po wcześniejszym zajęciu "4.1" i "4.17" przez RBC, zostaje "2.5" → odzysk "12.5"

order = [
    "PCT", "MCV", "RDW-SD", "PLT",
    "MCHC", "MCH", "RDW-CV",
    "P-LCR", "PDW", "MPV",
    "HCT",           # ← musi być przed WBC
    "WBC", "RBC",
    "HGB",           # ← musi być ostatnie
]
```

### 5.4 Odtwarzanie uciętych cyfr

OCR na skanach niskiej jakości może uciąć lewy skraj liczby (bbox za ciasny). Np. HGB=12.5 OCR zwraca jako "2.5".

```python
def _try_recover_leading_digit(param, lo, hi, all_numbers, claimed) -> Optional[float]:
    """Próbuje dokleić prefix 1-9 i sprawdza czy wynik mieści się w zakresie."""
    mid = (lo + hi) / 2
    best_val, best_dist = None, float("inf")

    for i, (val, bbox, src_text) in enumerate(all_numbers):
        if i in claimed:
            continue
        for prefix in range(1, 10):
            try:
                candidate = float(f"{prefix}{val}")
            except ValueError:
                continue
            if lo * 0.7 <= candidate <= hi * 1.3:
                dist = abs(candidate - mid)
                if dist < best_dist:
                    best_dist = dist
                    best_val = candidate

    return best_val
```

### 5.5 Generowanie alertów medycznych

```python
MEDICAL_ALERTS = [
    ("HGB",       "<",   11.5, "Możliwa anemia",                    "warning"),
    ("HGB",       "<",    8.0, "Ciężka anemia — pilne",             "critical"),
    ("WBC",       ">",   11.0, "Leukocytoza",                       "warning"),
    ("WBC",       ">",   30.0, "Znaczna leukocytoza — pilne",       "critical"),
    ("WBC",       "<",    2.0, "Leukopenia",                        "warning"),
    ("PLT",       "<",   50.0, "Małopłytkowość — pilne",            "critical"),
    ("PLT",       ">",  700.0, "Nadpłytkowość",                     "warning"),
    ("glukoza",   ">",  126.0, "Hiperglikemia na czczo",            "warning"),
    ("glukoza",   "<",   70.0, "Hipoglikemia",                      "critical"),
    ("TSH",       ">",    4.5, "Możliwa niedoczynność tarczycy",    "warning"),
    ("TSH",       "<",    0.4, "Możliwa nadczynność tarczycy",      "warning"),
    ("kreatynina",">",    1.3, "Podwyższona kreatynina",            "warning"),
    ("ALT",       ">",   56.0, "Podwyższona ALT (wątroba)",         "warning"),
    ("AST",       ">",   40.0, "Podwyższona AST (wątroba)",         "warning"),
]

def _generate_alerts(labs: dict) -> list:
    alerts = []
    for (param, op, threshold, message, level) in MEDICAL_ALERTS:
        val = labs.get(param, {}).get("value")
        if val is None:
            continue
        triggered = (op == "<" and val < threshold) or (op == ">" and val > threshold)
        if triggered:
            alerts.append({
                "param":     param,
                "value":     val,
                "threshold": threshold,
                "message":   message,
                "level":     level
            })
    return alerts
```

---

## 6. Jak dodać nowy typ dokumentu

### Krok 1 — Dodaj sygnaturę do classifier.py

```python
# api/ocr/classifier.py
_SIGNATURES["ekg"] = {
    "required_any": ["EKG", "elektrokardiogram", "zapis EKG"],
    "supporting":   ["rytm", "zatokowy", "HR", "QRS", "QTc", "ST", "PQ",
                     "blok", "migotanie", "trzepotanie", "bradykardia", "tachykardia"],
    "min_supporting": 2
}
```

### Krok 2 — Dodaj parser w parser.py

```python
def _parse_ekg(raw_text: str, text_lines) -> dict:
    result = {}

    hr_match = re.search(r"HR[:\s]+(\d{2,3})\s*/?\s*min", raw_text, re.I)
    if hr_match:
        result["HR"] = int(hr_match.group(1))

    if re.search(r"rytm zatokowy|sinus rhythm", raw_text, re.I):
        result["rhythm"] = "zatokowy"
    elif re.search(r"migotanie przedsionk", raw_text, re.I):
        result["rhythm"] = "migotanie_przedsionkow"

    qrs_match = re.search(r"QRS[:\s]+(\d+)\s*ms", raw_text, re.I)
    if qrs_match:
        result["QRS_ms"] = int(qrs_match.group(1))

    alerts = []
    hr = result.get("HR")
    if hr:
        if hr > 100:
            alerts.append({"param": "HR", "value": hr, "message": "Tachykardia", "level": "warning"})
        elif hr < 60:
            alerts.append({"param": "HR", "value": hr, "message": "Bradykardia", "level": "warning"})
        if hr > 150 or hr < 40:
            alerts[-1]["level"] = "critical"

    result["alerts"] = alerts
    return result
```

### Krok 3 — Podepnij w parse()

```python
def parse(doc_type: str, raw_text: str, text_lines) -> dict:
    if doc_type == "morphology":
        return _parse_morphology(raw_text, text_lines)
    elif doc_type == "lab_results":
        return _parse_lab_results(raw_text, text_lines)
    elif doc_type == "discharge":
        return _parse_discharge(raw_text, text_lines)
    elif doc_type == "ekg":
        return _parse_ekg(raw_text, text_lines)      # ← nowe
    else:
        return {"raw": raw_text, "alerts": []}
```

### Krok 4 — Zaktualizuj MedicalResultView.tsx

```tsx
// panel/src/components/MedicalResultView.tsx

{data.doc_type === "ekg" && data.parsed_data && (
  <div className="grid grid-cols-2 gap-3 mb-4">
    <div className="bg-slate-50 rounded-lg p-3">
      <div className="text-xs text-slate-500">Tętno (HR)</div>
      <div className="text-2xl font-bold text-slate-800">
        {data.parsed_data.HR ?? "—"} <span className="text-sm font-normal">/min</span>
      </div>
    </div>
    <div className="bg-slate-50 rounded-lg p-3">
      <div className="text-xs text-slate-500">Rytm</div>
      <div className="text-lg font-semibold text-slate-800">
        {data.parsed_data.rhythm ?? "—"}
      </div>
    </div>
  </div>
)}
```

### Krok 5 — Napisz testy

```python
# api/tests/test_parser.py

def test_classify_ekg():
    text = "Zapis EKG — rytm zatokowy miarowy\nHR: 72 /min\nQRS 80ms"
    assert classify(text) == "ekg"

def test_ekg_normal():
    text = "EKG\nHR: 72 /min\nRytm zatokowy QRS 90ms QTc 420ms"
    result = parse("ekg", text, [])
    assert result["HR"] == 72
    assert result["rhythm"] == "zatokowy"
    assert result["alerts"] == []

def test_ekg_tachykardia():
    text = "EKG\nHR: 130 /min\nRytm zatokowy"
    result = parse("ekg", text, [])
    assert any(a["message"] == "Tachykardia" for a in result["alerts"])
```

---

## 7. Jak dodać nowy parametr laboratoryjny

### Parametr morfologiczny (z zakresem referencyjnym)

```python
# api/ocr/parser.py — dodaj do _REF_CHAR
# Format: (nazwa, lo_min, lo_max, hi_min, hi_max)
# Wartości = granice tolerancji dla dopasowania zakresu z OCR

_REF_CHAR = [
    ...
    ("NRBC", 0.00, 0.01, 0.10, 0.20),   # normoblasty, zakres: 0.0-0.10
]

# Dodaj do listy kolejności (order) w _extract_ilaw_morph_labs()
order = [
    "PCT", "MCV", "RDW-SD", "PLT",
    "MCHC", "MCH", "RDW-CV",
    "NRBC",      # ← nowy parametr
    "P-LCR", "PDW", "MPV",
    "HCT", "WBC", "RBC", "HGB",
]
```

### Parametr biochemiczny (regex)

```python
# api/ocr/parser.py — w _parse_lab_results()

# Witamina B12
b12_match = re.search(
    r"witamina\s*B\s*12\s*[\:\s]+(\d+[\.,]?\d*)\s*(pg/mL|pmol/L)?",
    raw_text, re.I
)
if b12_match:
    val = float(b12_match.group(1).replace(",", "."))
    labs["witamina_B12"] = {
        "value":  val,
        "unit":   b12_match.group(2) or "pg/mL",
        "ref_lo": 197.0,
        "ref_hi": 866.0
    }
```

### Alert dla nowego parametru

```python
# api/ocr/parser.py — MEDICAL_ALERTS
MEDICAL_ALERTS = [
    ...
    ("witamina_B12", "<", 197.0, "Niedobór witaminy B12",         "warning"),
    ("witamina_B12", "<",  100.0, "Ciężki niedobór witaminy B12", "critical"),
    ("NRBC",         ">",    0.1, "Normoblasty we krwi — pilne",  "critical"),
]
```

---

## 8. Frontend — Next.js deep dive

### 8.1 Auth flow

```
Użytkownik → /login
  → POST /v1/auth/login { email, password }
  ← { token: "eyJ...", api_key: "mk_..." }
  → localStorage.setItem("ikzocr_token", token)
  → localStorage.setItem("ikzocr_api_key", api_key)
  → redirect /scan

Chronione strony:
  ConditionalLayout.tsx sprawdza isAuthenticated()
    → jeśli false: router.push("/login")

Każde żądanie API:
  apiKeyHeaders() → { Authorization: "Bearer <api_key>" }
```

### 8.2 lib/api.ts — pełna struktura

```typescript
// panel/src/lib/api.ts

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function apiKeyHeaders(): HeadersInit {
    const key = localStorage.getItem("ikzocr_api_key") ?? ""
    return { Authorization: `Bearer ${key}` }
}

// ─── Skanowanie ──────────────────────────────────────────────────────────────

export async function scanDocument(file: File): Promise<ScanResult> {
    const fd = new FormData()
    fd.append("file", file)
    const res = await fetch(`${BASE}/v1/scan`, {
        method: "POST",
        headers: apiKeyHeaders(),
        body: fd
    })
    if (!res.ok) throw new Error(await res.text())
    return res.json()
}

// ─── Historia ────────────────────────────────────────────────────────────────

export async function listDocuments(limit = 50, offset = 0): Promise<DocumentListItem[]> {
    const res = await fetch(
        `${BASE}/v1/documents?limit=${limit}&offset=${offset}`,
        { headers: apiKeyHeaders() }
    )
    if (!res.ok) throw new Error("Błąd pobierania listy")
    return res.json()
}

export async function getDocument(scanId: string): Promise<ScanResult> {
    const res = await fetch(`${BASE}/v1/documents/${scanId}`, {
        headers: apiKeyHeaders()
    })
    if (!res.ok) throw new Error("Nie znaleziono dokumentu")
    return res.json()
}

// ─── Export / pobieranie ─────────────────────────────────────────────────────

async function _downloadScan(scanId: string, ext: "txt" | "md" | "csv") {
    const res = await fetch(`${BASE}/v1/documents/${scanId}/export.${ext}`, {
        headers: apiKeyHeaders()
    })
    if (!res.ok) throw new Error(`Błąd pobierania .${ext}`)
    const blob = await res.blob()
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement("a")
    a.href     = url
    a.download = `ikzocr_${scanId.slice(0, 8)}.${ext}`
    a.click()
    URL.revokeObjectURL(url)
}

export const downloadScanTxt = (id: string) => _downloadScan(id, "txt")
export const downloadScanMd  = (id: string) => _downloadScan(id, "md")
export const downloadScanCsv = (id: string) => _downloadScan(id, "csv")

// ─── Klucze API ──────────────────────────────────────────────────────────────

export async function createApiKey(name: string): Promise<{ key: string; id: string }> {
    const res = await fetch(`${BASE}/v1/api-keys`, {
        method: "POST",
        headers: { ...apiKeyHeaders(), "Content-Type": "application/json" },
        body: JSON.stringify({ name, daily_limit: 200 })
    })
    if (!res.ok) throw new Error("Błąd tworzenia klucza")
    return res.json()
}
```

### 8.3 ConditionalLayout — ochrona tras

```tsx
// panel/src/components/ConditionalLayout.tsx
"use client"
import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { isAuthenticated } from "@/lib/auth"
import Sidebar from "./Sidebar"

const PUBLIC_PATHS = ["/login", "/register"]

export default function ConditionalLayout({ children }: { children: React.ReactNode }) {
    const router   = useRouter()
    const pathname = usePathname()
    const isPublic = PUBLIC_PATHS.includes(pathname)

    useEffect(() => {
        if (!isPublic && !isAuthenticated()) {
            router.push("/login")
        }
    }, [pathname])

    if (isPublic) {
        return <>{children}</>
    }

    return (
        <div className="flex h-screen bg-slate-50">
            <Sidebar />
            <main className="flex-1 overflow-auto">
                {children}
            </main>
        </div>
    )
}
```

### 8.4 Zmienne środowiskowe frontendu

| Zmienna | Dev | Prod |
|---------|-----|------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | `https://api.ikzocr.pl` |
| `NEXT_PUBLIC_APP_NAME` | `IKZOCR Dev` | `IKZOCR` |

Zmienne `NEXT_PUBLIC_*` są wbudowywane w bundle podczas `next build`. Zmiana wymaga rebuildu obrazu Docker.

---

## 9. Baza danych — migracje i schematy

### 9.1 Pełny schemat init.sql

Patrz [`init.sql`](../init.sql) w katalogu głównym projektu. Schemat tworzony automatycznie przy pierwszym uruchomieniu PostgreSQL.

### 9.2 Ręczna migracja na produkcji

```bash
# Podłącz się do bazy
docker compose exec postgres psql -U medyk -d medykocr

# Przykładowe migracje

-- Dodanie kolumny
ALTER TABLE scans ADD COLUMN IF NOT EXISTS page_count INTEGER DEFAULT 1;

-- Dodanie indeksu (bez blokowania tabel - CONCURRENTLY)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scans_confidence
  ON scans(confidence);

-- Zmiana rozmiaru kolumny
ALTER TABLE organizations ALTER COLUMN name TYPE VARCHAR(200);
```

### 9.3 Przydatne zapytania diagnostyczne

```sql
-- Statystyki skanowań per plan
SELECT ak.plan, COUNT(s.id) as scans, ROUND(AVG(s.confidence)::numeric, 3) as avg_conf
FROM scans s
JOIN api_keys ak ON s.api_key_id = ak.id
WHERE s.created_at > NOW() - INTERVAL '30 days'
GROUP BY ak.plan
ORDER BY scans DESC;

-- Najczęstsze typy dokumentów
SELECT doc_type, COUNT(*) as cnt
FROM scans
GROUP BY doc_type
ORDER BY cnt DESC;

-- Rozmiar tabel
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) as size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Ostatnie skany z alertami krytycznymi
SELECT s.id, s.created_at, s.parsed_json->'alerts' as alerts
FROM scans s
WHERE s.parsed_json @> '{"alerts": [{"level": "critical"}]}'
ORDER BY s.created_at DESC
LIMIT 20;

-- Klucze API z przekroczonym limitem dziennym
SELECT ak.name, ak.daily_limit,
       COUNT(s.id) FILTER (WHERE s.created_at::date = CURRENT_DATE) as today_scans
FROM api_keys ak
LEFT JOIN scans s ON s.api_key_id = ak.id
GROUP BY ak.id, ak.name, ak.daily_limit
HAVING COUNT(s.id) FILTER (WHERE s.created_at::date = CURRENT_DATE) >= ak.daily_limit;
```

---

## 10. Testowanie

### 10.1 Uruchomienie testów backendu

```bash
cd api
pip install pytest pytest-asyncio httpx

pytest tests/ -v                          # wszystkie testy
pytest tests/test_parser.py -v            # tylko parser
pytest tests/ -k "morphology" -v         # testy z "morphology" w nazwie
pytest tests/ --tb=short                  # krótsze traceback
```

### 10.2 Przykładowe testy parsera

```python
# api/tests/test_parser.py

from ocr.parser import parse
from ocr.classifier import classify

def test_classify_morphology():
    text = "Morfologia krwi\nHGB 14.2 g/dL\nWBC 6.5 10³/µL\nPLT 220"
    assert classify(text) == "morphology"

def test_classify_unknown():
    assert classify("Faktura VAT 23%\nNetto: 1000 PLN") is None

def test_hgb_ucięty_ocr():
    # "2.5" to HGB=12.5 ucięty przez OCR
    raw = "HGB  2.5  g/dL  12.0-16.0\nWBC  6.5  10³/µL  4.5-11.0"
    result = parse("morphology", raw, [])
    hgb = result.get("labs", {}).get("HGB", {})
    assert hgb.get("value") == 12.5

def test_critical_alert_anemia():
    raw = "HGB 7.2 g/dL  12.0-16.0"
    result = parse("morphology", raw, [])
    critical = [a for a in result.get("alerts", []) if a["level"] == "critical"]
    assert any(a["param"] == "HGB" for a in critical)

def test_hct_przed_wbc():
    # HCT=38.9 → OCR zwraca "8.9" → musi trafić do HCT, nie WBC
    raw = "HCT  8.9  %  35.0-47.0\nWBC  6.5  10³/µL  4.5-11.0"
    result = parse("morphology", raw, [])
    labs = result.get("labs", {})
    assert labs.get("HCT", {}).get("value") == 38.9
    assert labs.get("WBC", {}).get("value") == 6.5

def test_pesel_maskowany():
    raw = "PESEL: 85031200000"
    result = parse("morphology", raw, [])
    pesel = result.get("patient", {}).get("pesel", "")
    assert "*" in pesel
    assert pesel != "85031200000"
```

### 10.3 Testy integracyjne endpointów

```python
# api/tests/test_endpoints.py

from fastapi.testclient import TestClient
from main import app

client   = TestClient(app)
TEST_KEY = "Bearer mk_devkey_test123"

def test_health():
    r = client.get("/health")
    assert r.status_code == 200

def test_unauthorized():
    r = client.post("/v1/scan")
    assert r.status_code in (401, 422)

def test_invalid_key():
    r = client.post(
        "/v1/scan",
        headers={"Authorization": "Bearer invalid"},
        files={"file": ("t.jpg", b"\xff\xd8", "image/jpeg")}
    )
    assert r.status_code == 401

def test_list_documents():
    r = client.get("/v1/documents", headers={"Authorization": TEST_KEY})
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_export_route_not_captured_as_scan_id():
    # Sprawdza że /v1/documents/export nie jest traktowane jako scan_id
    r = client.get("/v1/documents/export", headers={"Authorization": TEST_KEY})
    # Powinien zwrócić CSV (200), nie 422 ("export" to nie UUID)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
```

---

## 11. Zmienne środowiskowe

### Backend (api/.env)

| Zmienna | Domyślna | Opis |
|---------|----------|------|
| `DATABASE_URL` | `postgresql://medyk:medyk@postgres:5432/medykocr` | Connection string PostgreSQL |
| `REDIS_URL` | `redis://redis:6379` | Connection string Redis |
| `CORS_ORIGINS` | `http://localhost:3000` | Dozwolone origins (przecinek dla wielu) |
| `PRELOAD_MODELS` | `true` | Ładowanie Surya przy starcie (`false` dla dev) |
| `TORCH_DEVICE` | `cpu` | `cpu` / `cuda` / `mps` |
| `MAX_FILE_SIZE_MB` | `20` | Max rozmiar uploadowanego pliku |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `JWT_SECRET` | *(wymagana w prod)* | Min. 32 losowe znaki |
| `JWT_EXPIRE_HOURS` | `24` | Czas życia JWT tokenu |

### Frontend (panel/.env.local)

| Zmienna | Opis |
|---------|------|
| `NEXT_PUBLIC_API_URL` | URL backendu, np. `https://api.ikzocr.pl` |
| `NEXT_PUBLIC_APP_NAME` | Nazwa w UI (domyślnie `IKZOCR`) |

---

## 12. Debugowanie typowych problemów

### OCR API nie startuje — modele nie ładują się

```bash
docker compose logs ocr-api | grep -i "error\|warning\|model"

# Jeśli "No space left" — wolumeny modeli zajmują ~2 GB
df -h
docker system prune --volumes   # UWAGA: usuwa dane!

# Jeśli "CUDA out of memory"
# W api/.env:
TORCH_DEVICE=cpu
docker compose restart ocr-api
```

### Błąd 500 przy GET /v1/documents/export

```bash
# Sprawdź kolejność tras
grep -n "@app.get" api/main.py
# export MUSI być przed {scan_id} — patrz sekcja 4.1
```

### Panel nie łączy się z API — błąd CORS

```bash
# W api/.env:
CORS_ORIGINS=http://localhost:3000,https://panel.ikzocr.pl
docker compose restart ocr-api

# Weryfikacja
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8000/v1/scan -v
# Szukaj: Access-Control-Allow-Origin: http://localhost:3000
```

### Imię pacjenta zawiera śmieci z innej kolumny

```bash
# Sprawdź regex _IMIE_ONLY_RE w parser.py:
# Musi mieć (?:[ ]{2,}|\s*\n|$) na końcu — zatrzymuje przy 2+ spacjach
grep -n "_IMIE_ONLY_RE" api/ocr/parser.py
```

### Baza PostgreSQL nie startuje

```bash
docker compose logs postgres | tail -20

# Najczęstsza przyczyna: permission error na volumes
ls -la $(docker volume inspect ikzocr_postgres_data --format '{{.Mountpoint}}')

# Reset (UWAGA: usuwa dane!)
docker compose down postgres
docker volume rm ikzocr_postgres_data
docker compose up -d postgres
```

### Wolne skanowanie (>60s)

```bash
# Sprawdź użycie zasobów podczas skanowania
docker stats --no-stream

# Jeśli CPU 100% → normalne dla CPU-only Surya
# Rozwiązania:
# 1. GPU: TORCH_DEVICE=cuda
# 2. Ogranicz rozmiar obrazu przed OCR (kompresja na wejściu)
# 3. Skaluj poziomo (więcej replik ocr-api)
```

---

## 13. Workflow CI/CD

### Obecny flow (ręczny na prod)

```bash
# Na serwerze
cd /opt/ikzocr
git pull origin main

docker compose build ocr-api   # po zmianie kodu/requirements
docker compose up -d --no-deps --force-recreate ocr-api

# Sprawdź czy wystartował
sleep 10
curl http://localhost:8000/health
```

### Watchtower — automatyczny update (On-Premise)

Watchtower sprawdza Docker Hub co 24h i restartuje kontenery jeśli jest nowy obraz. Dane w volumach są bezpieczne — Watchtower nie dotyka volumów.

```yaml
# docker-compose.yml
watchtower:
    image: containrrr/watchtower
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      WATCHTOWER_POLL_INTERVAL: "86400"
      WATCHTOWER_CLEANUP: "true"
    restart: unless-stopped
```

---

## 14. Konwencje kodu

### Python

- **Formatter:** `black --line-length 100`
- **Linter:** `ruff check . --fix`
- **Type hints:** wymagane dla wszystkich publicznych funkcji
- **Nazewnictwo:** `snake_case` dla funkcji/zmiennych, `PascalCase` dla klas
- **Prywatne funkcje:** prefix `_` (np. `_extract_ilaw_morph_labs`)
- **Stałe:** `UPPER_CASE` lub `_UPPER_CASE` jeśli prywatne modułu
- **Async I/O:** `async/await` dla bazy i Redis; `asyncio.to_thread()` dla blokującego OCR

```bash
cd api
black . --line-length 100
ruff check . --fix
mypy . --ignore-missing-imports
```

### TypeScript / React

- **Formatter:** Prettier (konfiguracja w `panel/.prettierrc` jeśli jest, inaczej domyślna Next.js)
- **Linter:** ESLint (`npm run lint`)
- **Komponenty:** funkcyjne z hooks, nigdy class components
- **Props:** zawsze typowane — `interface ComponentNameProps`
- **API calls:** wyłącznie przez `lib/api.ts`, nigdy bezpośrednio `fetch()` w komponentach
- **Styl:** Tailwind utility classes, unikaj inline styles

### Commit messages

```
feat: dodaj obsługę dokumentów EKG
fix: napraw ekstrakcję HGB (ucięta cyfra przez OCR)
fix: popraw kolejność tras FastAPI (export przed scan_id)
refactor: wyodrębnij _reconstruct_layout do osobnej funkcji
docs: rozszerz ARCHITECTURE.md o ADR
test: dodaj testy dla klasyfikatora EKG
chore: zaktualizuj surya-ocr do 0.6.2
```
