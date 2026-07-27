# IKZOCR — Architektura systemu

## Spis treści

1. [Przegląd wysokopoziomowy](#1-przegląd-wysokopoziomowy)
2. [Diagram sieci i kontenerów](#2-diagram-sieci-i-kontenerów)
3. [Przepływ danych — skanowanie dokumentu](#3-przepływ-danych--skanowanie-dokumentu)
4. [Komponent OCR API (FastAPI)](#4-komponent-ocr-api-fastapi)
5. [Silnik OCR — Surya](#5-silnik-ocr--surya)
6. [Parser i klasyfikator dokumentów](#6-parser-i-klasyfikator-dokumentów)
7. [Baza danych PostgreSQL](#7-baza-danych-postgresql)
8. [Cache i kolejka — Redis](#8-cache-i-kolejka--redis)
9. [Panel webowy (Next.js)](#9-panel-webowy-nextjs)
10. [Monitoring — Prometheus + Grafana](#10-monitoring--prometheus--grafana)
11. [Bezpieczeństwo i autoryzacja](#11-bezpieczeństwo-i-autoryzacja)
12. [Architektura On-Premise](#12-architektura-on-premise)
13. [Skalowanie i HA](#13-skalowanie-i-ha)
14. [Zależności zewnętrzne](#14-zależności-zewnętrzne)
15. [Decyzje architektoniczne (ADR)](#15-decyzje-architektoniczne-adr)

---

## 1. Przegląd wysokopoziomowy

IKZOCR to platforma SaaS do automatycznego rozpoznawania i strukturyzowania danych z dokumentów medycznych. System działa w modelu wielodostępnym (multi-tenant) z izolacją na poziomie kluczy API i organizacji.

```
                        ┌──────────────────────────────────────┐
                        │            INTERNET                  │
                        └──────────────┬───────────────────────┘
                                       │
                        ┌──────────────▼───────────────────────┐
                        │      NGINX (reverse proxy)           │
                        │  ・SSL termination (TLS 1.3)         │
                        │  ・Rate limiting (nginx limit_req)   │
                        │  ・gzip kompresja                    │
                        │  ・Static files (panel build)        │
                        └──────┬───────────────────┬───────────┘
                               │                   │
                 panel.ikzocr.pl              api.ikzocr.pl
                        :443                       :443
                               │                   │
               ┌───────────────▼──┐     ┌──────────▼──────────────┐
               │   PANEL          │     │   OCR API               │
               │   Next.js :3000  │     │   FastAPI :8000         │
               │                  │◄────│                         │
               │  ・SSR/CSR       │     │  ・REST API             │
               │  ・JWT auth      │     │  ・Bearer auth          │
               │  ・Tailwind UI   │     │  ・Async workers        │
               └──────────────────┘     └──────────┬──────────────┘
                                                   │
                        ┌──────────────────────────┼──────────────────────────┐
                        │                          │                          │
               ┌────────▼────────┐    ┌────────────▼──────────┐   ┌──────────▼──────┐
               │   Surya OCR     │    │   PostgreSQL :5432    │   │   Redis :6379   │
               │   (AI model)    │    │                       │   │                 │
               │                 │    │  ・scans              │   │  ・rate limit   │
               │  ・Detection    │    │  ・api_keys           │   │  ・scan counter │
               │  ・Recognition  │    │  ・users              │   │  ・job queue    │
               │  ・Layout       │    │  ・organizations      │   │  ・session TTL  │
               └─────────────────┘    └───────────────────────┘   └─────────────────┘
```

---

## 2. Diagram sieci i kontenerów

Wszystkie kontenery działają w ramach Docker Compose z dedykowaną siecią wewnętrzną `ikzocr_net`. Tylko NGINX eksponuje porty na zewnątrz.

```
Host OS (Ubuntu 22.04 LTS)
│
├── Docker network: ikzocr_net (bridge, 172.20.0.0/16)
│   │
│   ├── nginx          172.20.0.2   ports: 80→80, 443→443   ← jedyny port publiczny
│   ├── ocr-api        172.20.0.3   port 8000 (tylko internal)
│   ├── panel          172.20.0.4   port 3000 (tylko internal)
│   ├── postgres       172.20.0.5   port 5432 (tylko internal)
│   ├── redis          172.20.0.6   port 6379 (tylko internal)
│   ├── prometheus     172.20.0.7   port 9090 (tylko internal / VPN)
│   └── grafana        172.20.0.8   port 3001 (tylko internal / VPN)
│
├── Volumes (persistent)
│   ├── postgres_data  → /var/lib/postgresql/data
│   ├── redis_data     → /data
│   ├── grafana_data   → /var/lib/grafana
│   └── models_cache   → /root/.cache/surya  (modele AI ~2GB)
│
└── Host filesystem
    ├── /opt/ikzocr/          ← root projektu
    ├── /opt/ikzocr/api/      ← kod backendu
    ├── /opt/ikzocr/panel/    ← kod frontendu
    └── /etc/nginx/           ← konfiguracja nginx
```

### Konfiguracja NGINX

```nginx
# /etc/nginx/sites-available/ikzocr

# Przekierowanie HTTP → HTTPS
server {
    listen 80;
    server_name panel.ikzocr.pl api.ikzocr.pl;
    return 301 https://$host$request_uri;
}

# Panel Next.js
server {
    listen 443 ssl http2;
    server_name panel.ikzocr.pl;

    ssl_certificate     /etc/letsencrypt/live/ikzocr.pl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ikzocr.pl/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://172.20.0.4:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# OCR API
server {
    listen 443 ssl http2;
    server_name api.ikzocr.pl;

    # Rate limiting: 10 req/s burst 20
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://172.20.0.3:8000;
        client_max_body_size 25M;      # max rozmiar dokumentu
        proxy_read_timeout   120s;     # OCR może trwać do 2 min
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 3. Przepływ danych — skanowanie dokumentu

### 3.1 Ścieżka szczęśliwa (happy path)

```
Klient                    NGINX             OCR API              Surya            PostgreSQL
   │                        │                  │                    │                  │
   │── POST /v1/scan ───────►│                  │                    │                  │
   │   Authorization: Bearer │                  │                    │                  │
   │   Content-Type: multipart│                 │                    │                  │
   │   file=<obraz/PDF>      │                  │                    │                  │
   │                         │── proxy ────────►│                    │                  │
   │                         │                  │── verify API key ──────────────────►│
   │                         │                  │◄── api_key row ────────────────────│
   │                         │                  │                    │                  │
   │                         │                  │── check rate limit (Redis INCR)      │
   │                         │                  │                    │                  │
   │                         │                  │── load_image() ───►│                  │
   │                         │                  │                    │── det model      │
   │                         │                  │                    │── rec model      │
   │                         │                  │                    │── layout         │
   │                         │                  │◄── text_lines[] ──│                  │
   │                         │                  │                    │                  │
   │                         │                  │── classify() → doc_type              │
   │                         │                  │── parse() → labs{}, alerts[]         │
   │                         │                  │                    │                  │
   │                         │                  │── INSERT INTO scans ────────────────►│
   │                         │                  │◄── scan_id ─────────────────────────│
   │                         │                  │                    │                  │
   │◄────────────── 200 JSON ─────────────────│                    │                  │
   │  {scan_id, doc_type,    │                  │                    │                  │
   │   parsed_data, alerts}  │                  │                    │                  │
```

### 3.2 Szczegółowy pipeline OCR (wewnątrz OCR API)

```python
# Uproszczony pseudo-kod processor.py

def process(image_bytes: bytes) -> dict:

    # 1. Przygotowanie obrazu
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img = auto_rotate(img)          # EXIF orientation fix
    img = enhance_contrast(img)     # CLAHE dla skanów niskiej jakości

    # 2. Surya — wykrywanie tekstu (detection model)
    det_result = batch_text_detection([img], det_model, det_processor)
    # → bboxes: [{"bbox": [x1,y1,x2,y2], "confidence": 0.97}, ...]

    # 3. Surya — rozpoznawanie tekstu (recognition model)
    rec_result = run_recognition([img], [det_result[0].bboxes], rec_model, rec_processor)
    # → text_lines: [{"text": "HGB", "bbox": [...], "confidence": 0.94}, ...]

    # 4. Rekonstrukcja układu strony
    raw_text = _reconstruct_layout(rec_result[0].text_lines)
    # → sortowanie po Y→X, wstawianie proporcjonalnych spacji między kolumnami

    # 5. Klasyfikacja dokumentu
    doc_type = classify(raw_text)
    # → "morphology" | "lab_results" | "discharge" | "prescription" | ...

    # 6. Parsowanie danych
    parsed = parse(doc_type, raw_text, rec_result[0].text_lines)
    # → {"patient": {...}, "labs": {...}, "alerts": [...]}

    return parsed
```

### 3.3 Rekonstrukcja układu strony

Problem: Surya wykrywa kolumny tabeli laboratoryjnej jako osobne bloki tekstu w kolejności od góry do dołu **każdej kolumny** — nie w naturalnej kolejności czytania (lewa→prawa). Kolumna "Wynik" może więc pojawić się przed kolumną "Parametr".

Rozwiązanie: `_reconstruct_layout()` grupuje linie według osi Y (ten sam wiersz = Y1 zbliżone do siebie w tolerancji ±8px), a wewnątrz wiersza sortuje po X1. Pomiędzy liniami wstawia proporcjonalne spacje zgodnie z odległością poziomą.

```
Przed rekonstrukcją (kolejność Surya):     Po rekonstrukcji:
  "HGB"      (x=50,  y=120)               "HGB    14.2   g/dL   12.0-17.5"
  "WBC"      (x=50,  y=145)               "WBC     8.9  10³/µL   4.5-11.0"
  "RBC"      (x=50,  y=170)               "RBC     4.1  10⁶/µL   4.0-5.5"
  "14.2"     (x=200, y=120)
  "8.9"      (x=200, y=145)
  "4.1"      (x=200, y=170)
  "g/dL"     (x=290, y=120)
  ...
```

---

## 4. Komponent OCR API (FastAPI)

### 4.1 Struktura plików

```
api/
├── main.py          # Router, middleware, endpoint handlers
├── db.py            # Pool połączeń asyncpg, helper functions
├── schemas.py       # Modele Pydantic (request/response/DB)
├── requirements.txt # Zależności Python
├── Dockerfile
└── ocr/
    ├── __init__.py
    ├── processor.py   # Wrapper Surya: ładowanie modeli, przetwarzanie obrazu
    ├── classifier.py  # Wykrywanie typu dokumentu na podstawie słów kluczowych
    └── parser.py      # Ekstrakcja danych: morfologia, lab, PESEL, daty, alerty
```

### 4.2 Inicjalizacja i ładowanie modeli

Modele Surya (~1.5 GB) ładowane są **raz przy starcie** kontenera i trzymane w pamięci przez cały czas życia procesu. Pierwsze uruchomienie pobiera modele z HuggingFace Hub do `~/.cache/surya`.

```python
# main.py — startup event
@app.on_event("startup")
async def startup():
    await db.init_pool()           # pula asyncpg (min=2, max=10 połączeń)
    processor.preload_models()     # det + rec model do RAM/VRAM
    logger.info("Models loaded. Ready.")
```

Zmienna `PRELOAD_MODELS=true` w `.env` kontroluje czy modele ładują się przy starcie (prod) czy przy pierwszym żądaniu (dev — szybszy restart).

### 4.3 Middleware i autoryzacja

```python
# Każde żądanie do /v1/* przechodzi przez verify_api_key()
async def verify_api_key(authorization: str = Header(...)) -> ApiKey:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    
    raw_key = authorization[7:]
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    row = await db.fetchrow(
        "SELECT * FROM api_keys WHERE key_hash=$1 AND active=true", key_hash
    )
    if not row:
        raise HTTPException(401, "Invalid API key")
    
    return ApiKey(**row)
```

### 4.4 Routing i kolejność tras

**Krytyczne:** trasy statyczne muszą być zdefiniowane PRZED trasami z parametrami dynamicznymi, inaczej FastAPI dopasuje `/v1/documents/export` jako `{scan_id}="export"`.

```python
# POPRAWNA kolejność w main.py:
@app.get("/v1/documents/export")          # ← statyczna, PIERWSZA
@app.get("/v1/documents/export.md")       # ← statyczna
@app.get("/v1/documents/{scan_id}")       # ← dynamiczna, PO statycznych
@app.get("/v1/documents/{scan_id}/export.txt")
@app.get("/v1/documents/{scan_id}/export.md")
@app.get("/v1/documents/{scan_id}/export.csv")
```

### 4.5 Obsługa plików wejściowych

```python
@app.post("/v1/scan")
async def scan_document(
    file: UploadFile = File(...),
    api_key: ApiKey = Depends(verify_api_key)
):
    # Walidacja rozmiaru
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(413, "Plik zbyt duży (max 20MB)")
    
    # Walidacja magic bytes (nie ufamy Content-Type klienta)
    mime = magic.from_buffer(content, mime=True)
    if mime not in ("image/jpeg", "image/png", "image/tiff", "application/pdf"):
        raise HTTPException(415, f"Nieobsługiwany format: {mime}")
    
    # PDF → pierwsza strona jako obraz
    if mime == "application/pdf":
        content = pdf_to_image(content)
    
    # Sprawdź limit skanów (Redis)
    count_key = f"scan_count:{api_key.id}:{date.today().isoformat()}"
    daily_count = await redis.incr(count_key)
    await redis.expire(count_key, 86400)
    if daily_count > api_key.daily_limit:
        raise HTTPException(429, "Dzienny limit skanów wyczerpany")
    
    # Przetwarzanie OCR (może trwać 5–60s)
    result = await asyncio.to_thread(processor.process, content)
    
    # Zapis do bazy
    scan_id = await db.save_scan(api_key.id, result)
    
    return {"scan_id": scan_id, **result}
```

---

## 5. Silnik OCR — Surya

### 5.1 Architektura modeli Surya

Surya składa się z dwóch niezależnych modeli:

```
┌─────────────────────────────────────────────────────────────┐
│                   SURYA PIPELINE                            │
│                                                             │
│  Input: PIL.Image (RGB)                                     │
│       │                                                     │
│       ▼                                                     │
│  ┌────────────────────────────────────────┐                 │
│  │  Detection Model (surya-det)           │                 │
│  │  Architektura: segmentation CNN        │                 │
│  │  Output: bounding boxes tekstu         │                 │
│  │  Format: [{bbox: [x1,y1,x2,y2],        │                 │
│  │            polygon: [...],             │                 │
│  │            confidence: 0.97}]          │                 │
│  └────────────────────┬───────────────────┘                 │
│                       │ bboxes                              │
│                       ▼                                     │
│  ┌────────────────────────────────────────┐                 │
│  │  Recognition Model (surya-rec)         │                 │
│  │  Architektura: Transformer (Donut)     │                 │
│  │  Input: wycięte fragmenty obrazu       │                 │
│  │  Output: tekst + confidence per bbox   │                 │
│  │  Obsługuje: PL, EN, DE i 90+ języków   │                 │
│  └────────────────────┬───────────────────┘                 │
│                       │ text_lines                          │
│                       ▼                                     │
│  ┌────────────────────────────────────────┐                 │
│  │  Layout Reconstruction (_reconstruct)  │                 │
│  │  Sortowanie Y→X, merge kolumn          │                 │
│  │  Output: raw_text (string)             │                 │
│  └────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Znane ograniczenia i obejścia

| Problem | Przyczyna | Obejście w kodzie |
|---------|-----------|-------------------|
| Kolumny tabeli w złej kolejności | Surya skanuje kolumny top-to-bottom | `_reconstruct_layout()` grupuje po Y |
| Przycięty wynik (np. "2.5" zamiast "12.5") | OCR nie widzi lewej cyfry na skraju bbox | `_try_recover_leading_digit()` w parser.py |
| Imię + tekst z sąsiedniej kolumny | Surya łączy bliskie kolumny w jedną linię | Regex `_IMIE_ONLY_RE` zatrzymuje się przy `[ ]{2,}` |
| PESEL: znaki podobne (0/O, 1/l) | Błędy OCR na niskiej jakości skanach | Normalizacja przez `_normalize_digits()` |

### 5.3 Wymagania sprzętowe

| Tryb | RAM | GPU | Czas skanowania (A4 scan) |
|------|-----|-----|--------------------------|
| CPU only | 8 GB | brak | 15–45s |
| GPU (CUDA) | 8 GB | 4GB VRAM | 3–8s |
| GPU (MPS Apple Silicon) | unified 16GB | unified | 5–12s |

Produkcja SaaS działa na CPU (VPS z 16 GB RAM). Dla instalacji On-Premise z GPU wystarczy `TORCH_DEVICE=cuda` w `.env`.

---

## 6. Parser i klasyfikator dokumentów

### 6.1 Klasyfikator

`classifier.py` analizuje raw_text za pomocą zestawu słów kluczowych i wzorców regex. Każdy typ dokumentu ma własny zestaw markerów i próg pewności.

```python
DOC_SIGNATURES = {
    "morphology": {
        "required": ["morfologia", "hemoglobina", "HGB", "WBC", "RBC"],
        "any_of":   ["erytrocyty", "leukocyty", "płytki", "PLT", "HCT"],
        "min_score": 2
    },
    "lab_results": {
        "required": [],
        "any_of":   ["glukoza", "kreatynina", "TSH", "FT4", "ALT", "cholesterol"],
        "min_score": 2
    },
    "discharge": {
        "required": ["karta informacyjna", "epikryza"],
        "any_of":   ["rozpoznanie", "ICD", "leczenie", "wypisano"],
        "min_score": 1
    },
    "prescription": {
        "required": ["Rp.", "recepta"],
        "any_of":   ["mg", "dawkowanie", "refundacja"],
        "min_score": 1
    }
}
```

### 6.2 Ekstrakcja morfologii — algorytm ref-range

Dla morfologii krwi IKZOCR używa zakresu referencyjnego jako "klucza" do identyfikacji parametru. Każdy parametr ma charakterystyczny zakres (np. HGB kobiety: 12.0–16.0, HGB mężczyźni: 14.0–18.0).

```python
# Tabela zakresów referencyjnych (lo_min, lo_max, hi_min, hi_max)
_REF_CHAR = [
    # param    lo_min  lo_max  hi_min  hi_max
    ("HGB",    11.0,   13.5,   15.0,   18.5),
    ("WBC",     3.07,   4.50,   9.50,  11.00),
    ("RBC",     3.80,   4.20,   5.00,   5.80),
    ("PLT",   130.0,  160.0,  350.0,  450.0),
    ("HCT",    34.1,   38.0,   44.9,   52.0),
    ("MCV",    78.0,   82.0,   96.0,  100.0),
    ("MCH",    26.0,   27.0,   33.0,   34.0),
    ("MCHC",   31.5,   32.0,   36.0,   37.0),
    ("RDW-CV", 10.5,   11.0,   14.5,   16.0),
    ("RDW-SD", 35.5,   42.0,   42.0,   58.0),  # lo_min=35.5 (nie 32.0!) — HCT range fix
    ("MPV",     6.5,    7.0,   11.0,   13.0),
    ("PDW",    10.0,   11.0,   16.0,   18.0),
    ("P-LCR",  15.0,   18.0,   35.0,   40.0),
    ("PCT",     0.15,   0.17,   0.35,   0.40),
]
```

**Kolejność przetwarzania jest krytyczna.** HCT musi być przetworzone przed WBC, bo OCR może zwrócić "8.9" (przyciętą wartość HCT=38.9) która mieści się w zakresie WBC [3.07, 10.95]:

```python
order = [
    "PCT", "MCV", "RDW-SD", "PLT",
    "MCHC", "MCH", "RDW-CV",
    "P-LCR", "PDW", "MPV",
    "HCT",   # ← musi być przed WBC
    "WBC", "RBC",
    "HGB",   # ← na końcu: tylko "2.5" pozostaje → odzyskuje "12.5"
]
```

### 6.3 Alerty medyczne

```python
MEDICAL_ALERTS = [
    # (parametr, operator, próg, komunikat, poziom)
    ("HGB",      "<",  11.5,  "Możliwa anemia",              "warning"),
    ("HGB",      "<",   8.0,  "Ciężka anemia — pilne",       "critical"),
    ("WBC",      ">",  11.0,  "Leukocytoza",                 "warning"),
    ("WBC",      ">",  30.0,  "Znaczna leukocytoza — pilne", "critical"),
    ("WBC",      "<",   2.0,  "Leukopenia",                  "warning"),
    ("PLT",      "<",  50.0,  "Małopłytkowość — pilne",      "critical"),
    ("PLT",      ">", 700.0,  "Nadpłytkowość",               "warning"),
    ("glukoza",  ">", 126.0,  "Hiperglikemia na czczo",      "warning"),
    ("glukoza",  "<",  70.0,  "Hipoglikemia",                "critical"),
    ("TSH",      ">",   4.5,  "Możliwa niedoczynność tarczycy", "warning"),
    ("TSH",      "<",   0.4,  "Możliwa nadczynność tarczycy",  "warning"),
    ("kreatynina",">",  1.3,  "Podwyższona kreatynina",      "warning"),
]
```

---

## 7. Baza danych PostgreSQL

### 7.1 Schemat ER

```
┌───────────────────┐       ┌───────────────────────┐
│   organizations   │       │        users           │
│───────────────────│       │───────────────────────│
│ id (UUID PK)      │◄──────│ id (UUID PK)          │
│ name              │       │ org_id (FK)           │
│ plan              │       │ email (UNIQUE)        │
│ scan_limit        │       │ password_hash         │
│ scans_used        │       │ role                  │
│ created_at        │       │ created_at            │
└───────────────────┘       └───────────────────────┘
         │
         │ 1:N
         ▼
┌───────────────────┐       ┌───────────────────────┐
│    api_keys       │       │        scans           │
│───────────────────│       │───────────────────────│
│ id (UUID PK)      │◄──────│ id (UUID PK)          │
│ org_id (FK)       │       │ api_key_id (FK)       │
│ key_hash (SHA256) │       │ doc_type              │
│ name              │       │ raw_text              │
│ plan              │       │ parsed_json (JSONB)   │
│ daily_limit       │       │ confidence            │
│ active            │       │ file_name             │
│ created_at        │       │ file_size             │
│ last_used_at      │       │ processing_time_ms    │
└───────────────────┘       │ created_at            │
                            └───────────────────────┘
```

### 7.2 Pełny schemat SQL

```sql
-- init.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'starter'
                    CHECK (plan IN ('starter','pro','enterprise')),
    scan_limit  INTEGER NOT NULL DEFAULT 200,
    scans_used  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'operator'
                      CHECK (role IN ('admin','operator','readonly')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE api_keys (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key_hash     TEXT NOT NULL UNIQUE,    -- SHA-256 hex
    name         TEXT NOT NULL,
    plan         TEXT NOT NULL DEFAULT 'starter',
    daily_limit  INTEGER NOT NULL DEFAULT 200,
    active       BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE TABLE scans (
    id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    api_key_id         UUID NOT NULL REFERENCES api_keys(id),
    doc_type           TEXT,
    raw_text           TEXT,
    parsed_json        JSONB,
    confidence         FLOAT,
    file_name          TEXT,
    file_size          INTEGER,
    processing_time_ms INTEGER,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indeksy
CREATE INDEX idx_scans_api_key_id   ON scans(api_key_id);
CREATE INDEX idx_scans_created_at   ON scans(created_at DESC);
CREATE INDEX idx_scans_doc_type     ON scans(doc_type);
CREATE INDEX idx_scans_parsed_json  ON scans USING GIN(parsed_json);
CREATE INDEX idx_api_keys_key_hash  ON api_keys(key_hash);
CREATE INDEX idx_users_email        ON users(email);
```

### 7.3 Przykładowa zawartość parsed_json

```json
{
  "patient": {
    "name": "ANNA KOWALSKA",
    "pesel": "XXXXXX*****",
    "birth_date": "1985-03-12",
    "facility": "Szpital Powiatowy w Iławie"
  },
  "labs": {
    "HGB":  { "value": 12.5, "unit": "g/dL",    "ref_lo": 12.0, "ref_hi": 16.0 },
    "WBC":  { "value":  6.2, "unit": "10³/µL",  "ref_lo":  4.5, "ref_hi": 11.0 },
    "RBC":  { "value":  4.1, "unit": "10⁶/µL",  "ref_lo":  3.8, "ref_hi":  5.2 },
    "PLT":  { "value": 220,  "unit": "10³/µL",  "ref_lo": 150,  "ref_hi": 400  },
    "HCT":  { "value": 38.4, "unit": "%",        "ref_lo": 35.0, "ref_hi": 47.0 }
  },
  "alerts": [
    { "param": "HGB", "value": 12.5, "threshold": 12.0,
      "message": "HGB blisko dolnej granicy normy", "level": "info" }
  ],
  "doc_type": "morphology",
  "exam_date": "2026-07-15",
  "confidence": 0.91
}
```

---

## 8. Cache i kolejka — Redis

### 8.1 Klucze Redis

| Klucz | TTL | Cel |
|-------|-----|-----|
| `scan_count:{api_key_id}:{YYYY-MM-DD}` | 86400s (1 dzień) | Dzienny licznik skanów per klucz |
| `ratelimit:{ip}:{minute}` | 60s | Rate limiting per IP |
| `session:{jwt_jti}` | 86400s | Blacklista unieważnionych JWT |
| `model_warm` | — | Flaga: modele załadowane do RAM |

### 8.2 Schemat rate limitingu

```
Każde żądanie POST /v1/scan:
  1. INCR scan_count:{api_key_id}:{today}
  2. Jeśli > daily_limit → 429 Too Many Requests
  3. EXPIRE scan_count:{api_key_id}:{today} 86400  (reset o północy)

Każde żądanie (nginx level):
  limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
  → max 10 req/s per IP, burst 20
```

---

## 9. Panel webowy (Next.js)

### 9.1 Struktura routingu

```
panel/src/app/
├── page.tsx              # / → redirect do /scan lub /login
├── login/page.tsx        # Logowanie (JWT)
├── register/page.tsx     # Rejestracja organizacji
├── scan/page.tsx         # Upload dokumentu + live preview wyniku
├── documents/page.tsx    # Historia skanów + pobieranie plików
├── api-keys/page.tsx     # Zarządzanie kluczami API
├── statistics/page.tsx   # Wykresy użycia (Chart.js)
├── facilities/page.tsx   # Placówki i plany subskrypcji
├── plan/page.tsx         # Aktualny plan + upgrade
└── layout.tsx            # Root layout (ConditionalLayout wrapper)
```

### 9.2 Warstwa API (lib/api.ts)

Wszystkie wywołania backendu przechodzą przez `lib/api.ts`. Klucz API przechowywany jest w `localStorage` pod kluczem `ikzocr_api_key`.

```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function apiKeyHeaders(): HeadersInit {
    const key = localStorage.getItem("ikzocr_api_key") ?? ""
    return { Authorization: `Bearer ${key}` }
}

// Scan — multipart/form-data
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

// Download helpers
async function _downloadScan(scanId: string, ext: "txt"|"md"|"csv") {
    const res = await fetch(`${BASE}/v1/documents/${scanId}/export.${ext}`, {
        headers: apiKeyHeaders()
    })
    if (!res.ok) throw new Error(`Błąd pobierania .${ext}`)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `ikzocr_${scanId.slice(0, 8)}.${ext}`
    a.click()
    URL.revokeObjectURL(url)
}

export const downloadScanTxt = (id: string) => _downloadScan(id, "txt")
export const downloadScanMd  = (id: string) => _downloadScan(id, "md")
export const downloadScanCsv = (id: string) => _downloadScan(id, "csv")
```

### 9.3 Komponent MedicalResultView

Główny komponent wyświetlający wynik OCR. Renderuje:
- Dane pacjenta (imię, PESEL zamaskowany, data badania, placówka)
- Tabelę wyników laboratoryjnych z kolorowaniem (wartość poza normą → czerwony)
- Alerty medyczne (critical → czerwony banner, warning → żółty)
- Pasek pobierania plików (.txt / .md / .csv)
- Surowy tekst OCR (collapsible)

---

## 10. Monitoring — Prometheus + Grafana

### 10.1 Metryki eksponowane przez OCR API

```python
# /metrics endpoint (prometheus_fastapi_instrumentator)
http_requests_total{method, endpoint, status}    # liczba żądań
http_request_duration_seconds{endpoint}          # histogramy czasu odpowiedzi
ocr_processing_seconds                           # czas samego OCR (bez HTTP)
ocr_scans_total{doc_type, status}               # skany wg typu i wyniku
ocr_confidence_histogram                         # rozkład pewności OCR
active_connections                               # aktywne połączenia asyncpg
```

### 10.2 Alerty Prometheus (alerting rules)

```yaml
# monitoring/prometheus_alerts.yml
groups:
  - name: ikzocr
    rules:
      - alert: APIDown
        expr: up{job="ocr-api"} == 0
        for: 1m
        annotations:
          summary: "OCR API jest niedostępne"

      - alert: HighOCRLatency
        expr: histogram_quantile(0.95, http_request_duration_seconds{endpoint="/v1/scan"}) > 60
        for: 5m
        annotations:
          summary: "P95 skanowania > 60s"

      - alert: LowDiskSpace
        expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes < 0.15
        for: 10m
        annotations:
          summary: "Dysk < 15% wolnego miejsca"
```

---

## 11. Bezpieczeństwo i autoryzacja

### 11.1 Model uwierzytelniania

```
Klient (API)               Klient (Panel)
     │                           │
     │ Bearer mk_xxxxx           │ POST /auth/login (email+password)
     │                           │ ← JWT {sub: user_id, org_id, role, exp}
     │                           │
     ▼                           ▼
OCR API verifies:           OCR API verifies:
  SHA-256(mk_xxxxx)           JWT signature + exp
  → match in api_keys         → user in users
  → check active=true         → check role permissions
  → check daily limit         → check org scan limit
```

### 11.2 Generowanie kluczy API

```python
import secrets, hashlib

def generate_api_key() -> tuple[str, str]:
    """Zwraca (raw_key, hash). raw_key pokazywany raz, hash zapisywany do DB."""
    random_part = secrets.token_urlsafe(18)   # 24 znaki base64url
    raw_key = f"mk_{random_part}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash
```

### 11.3 Izolacja danych między klientami (multi-tenancy)

Każde zapytanie do tabeli `scans` filtrowane przez `api_key_id`, który jest powiązany z `org_id`. Klient widzi tylko własne skany.

```sql
-- Każdy GET /v1/documents filtruje przez klucz API bieżącego żądania
SELECT * FROM scans
WHERE api_key_id = $1        -- $1 = api_key.id z nagłówka Authorization
ORDER BY created_at DESC
LIMIT 50;
```

---

## 12. Architektura On-Premise

W wariancie On-Premise klient instaluje ten sam obraz Docker na własnej infrastrukturze. Jedyna różnica: brak SMTP/webhook do zewnętrznych serwisów i pełna kontrola nad danymi.

```
Infrastruktura klienta (np. Szpital)
│
├── Serwer Linux (Ubuntu 22.04, min. 8 GB RAM, 4 vCPU, 100 GB dysk)
│   │
│   └── Docker Compose (ten sam stack)
│       ├── ocr-api
│       ├── panel
│       ├── postgres       ← dane NIGDY nie wychodzą na zewnątrz
│       ├── redis
│       └── nginx
│
├── Aktualizacje: Watchtower
│   └── co noc sprawdza nowe obrazy Docker Hub → restart jeśli nowy
│       → dane w postgres_data VOLUME nienaruszone
│
└── Backup: klient odpowiada za backup PostgreSQL
    └── Zalecany: pg_dump + transfer do bezpiecznego storage
```

### Watchtower — automatyczne aktualizacje bez utraty danych

```yaml
# docker-compose.yml fragment
watchtower:
    image: containrrr/watchtower
    volumes:
        - /var/run/docker.sock:/var/run/docker.sock
    environment:
        WATCHTOWER_POLL_INTERVAL: 86400     # sprawdzaj co 24h
        WATCHTOWER_CLEANUP: "true"          # usuń stare obrazy
        WATCHTOWER_INCLUDE_STOPPED: "false"
        WATCHTOWER_NOTIFICATIONS: "email"
        WATCHTOWER_NOTIFICATION_EMAIL_TO: "admin@klient.pl"
    restart: unless-stopped
```

---

## 13. Skalowanie i HA

### 13.1 Skalowanie poziome OCR API

OCR API jest bezstanowe — każda instancja jest niezależna. Stan (skany, klucze) w PostgreSQL i Redis.

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    │  (nginx/HAProxy)│
                    └───────┬─────────┘
                            │
               ┌────────────┼────────────┐
               ▼            ▼            ▼
         ocr-api:1     ocr-api:2    ocr-api:3
         (port 8001)  (port 8002)  (port 8003)
               │            │            │
               └────────────┼────────────┘
                            │
               ┌────────────┼────────────┐
               ▼                         ▼
          PostgreSQL                  Redis
          (primary)               (single / cluster)
```

### 13.2 Limity zasobów per kontener (zalecane dla prod)

```yaml
# docker-compose.yml
services:
  ocr-api:
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 12G
        reservations:
          cpus: "2"
          memory: 8G
  postgres:
    deploy:
      resources:
        limits:
          memory: 4G
  redis:
    deploy:
      resources:
        limits:
          memory: 512M
```

---

## 14. Zależności zewnętrzne

| Zależność | Wersja | Cel | Licencja |
|-----------|--------|-----|----------|
| surya-ocr | 0.6.x | Silnik OCR | GPL-3.0 |
| fastapi | 0.111+ | Framework HTTP | MIT |
| asyncpg | 0.29+ | Klient PostgreSQL | Apache-2.0 |
| pydantic | 2.x | Walidacja danych | MIT |
| pillow | 10.x | Przetwarzanie obrazów | HPND |
| redis-py | 5.x | Klient Redis | MIT |
| python-magic | 0.4.x | Detekcja MIME | MIT |
| next | 14.x | Frontend React | MIT |
| tailwindcss | 3.x | Style CSS | MIT |
| PostgreSQL | 16+ | Baza danych | PostgreSQL |
| Redis | 7.x | Cache | BSD-3 |

---

## 15. Decyzje architektoniczne (ADR)

### ADR-001: FastAPI zamiast Django/Flask

**Decyzja:** FastAPI jako backend.  
**Powód:** Natywna obsługa async (asyncpg, asyncio.to_thread dla blokującego OCR), automatyczna dokumentacja OpenAPI, Pydantic v2 dla walidacji, mniejszy narzut niż Django.  
**Kompromis:** Brak wbudowanego ORM (korzystamy z raw asyncpg queries).

### ADR-002: Surya zamiast Tesseract

**Decyzja:** Surya OCR jako silnik.  
**Powód:** Tesseract radzi sobie słabo z niestandarowym układem strony (tabele laboratoryjne). Surya obsługuje layout detection, co pozwala odtworzyć kolumny tabeli.  
**Kompromis:** Surya wymaga ~1.5 GB RAM na modele; Tesseract działa na 200 MB.

### ADR-003: JSONB w PostgreSQL zamiast osobnych tabel per parametr

**Decyzja:** Wyniki parsowania zapisywane jako JSONB w kolumnie `parsed_json`.  
**Powód:** Różne typy dokumentów mają zupełnie różną strukturę danych. JSONB z GIN index pozwala na elastyczne zapytania bez migracji schematu przy każdym nowym typie dokumentu.  
**Kompromis:** Trudniejsze zapytania agregujące (np. "średnia HGB w ostatnim miesiącu") — wymagają `parsed_json->>'labs'->'HGB'->>'value'`.

### ADR-004: Ref-range anchoring dla morfologii

**Decyzja:** Identyfikacja parametrów morfologii przez dopasowanie zakresu referencyjnego, nie nazwy parametru.  
**Powód:** OCR często myli polskie znaki i skróty (np. "HGS" zamiast "HGB", "W8C" zamiast "WBC"). Zakres referencyjny (np. "12.0-16.0" jest unikalny dla HGB kobiet) jest bardziej niezawodny niż tekst.  
**Kompromis:** Wrażliwość na niestandardowe zakresy referencyjne laboratoriów. Parametr `lo_min/lo_max` w `_REF_CHAR` musi być właściwie ustawiony — zbyt szeroki zakres powoduje kolizje między parametrami.
