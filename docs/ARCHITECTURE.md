# IKZOCR — Architektura systemu

## Diagram wysokopoziomowy

```
┌─────────────────────────────────────────────────────────────────┐
│                        KLIENT                                   │
│  Przeglądarka (panel.ikzocr.pl)  │  Aplikacja (REST API)        │
└─────────────────┬───────────────────────────┬───────────────────┘
                  │ HTTPS                     │ HTTPS + Bearer
                  ▼                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     NGINX (reverse proxy)                       │
│              SSL termination · rate limiting · gzip             │
└──────────┬──────────────────────────────────┬───────────────────┘
           │ :3000                            │ :8000
           ▼                                  ▼
┌──────────────────┐               ┌──────────────────────────────┐
│   PANEL (Next.js)│               │      OCR API (FastAPI)       │
│                  │               │                              │
│ ・Skanowanie     │               │  POST /v1/scan               │
│ ・Historia       │──── API ────▶ │  GET  /v1/documents          │
│ ・Klucze API     │               │  GET  /v1/documents/{id}     │
│ ・Statystyki     │               │  GET  /v1/documents/export   │
│ ・Placówki/plany │               │  GET  /v1/documents/{id}/    │
└──────────────────┘               │         export.{txt,md,csv}  │
                                   └──────┬───────────┬───────────┘
                                          │           │
                          ┌───────────────┘           └───────────────┐
                          ▼                                           ▼
               ┌──────────────────┐                     ┌────────────────────┐
               │   Surya OCR      │                     │   PostgreSQL       │
               │   (AI engine)    │                     │                    │
               │                  │                     │  scans             │
               │ ・Text detection │                     │  api_keys          │
               │ ・Layout recon.  │                     │  users             │
               │ ・Column merging │                     │  organizations     │
               └──────────────────┘                     └────────────────────┘
                                                                    │
                                                         ┌──────────┘
                                                         ▼
                                              ┌──────────────────┐
                                              │     Redis        │
                                              │                  │
                                              │  ・Rate limit    │
                                              │  ・Job queue     │
                                              │  ・Session cache │
                                              └──────────────────┘
```

## Komponenty

### OCR API (`api/`)

| Plik | Odpowiedzialność |
|------|-----------------|
| `main.py` | Endpointy FastAPI, auth middleware, eksport |
| `db.py` | Połączenie z PostgreSQL (asyncpg) |
| `schemas.py` | Modele Pydantic (request/response) |
| `ocr/processor.py` | Wrapper na Surya — konwersja obrazu, wywołanie modelu |
| `ocr/classifier.py` | Wykrywanie typu dokumentu (morfologia, epikryza, zwolnienie…) |
| `ocr/parser.py` | Ekstrakcja danych: wartości lab, PESEL, imię, daty, alerty |

### Panel (`panel/src/`)

| Ścieżka | Widok |
|---------|-------|
| `app/scan/` | Upload i podgląd wyniku OCR |
| `app/documents/` | Historia skanów + pobieranie plików |
| `app/api-keys/` | Zarządzanie kluczami API |
| `app/statistics/` | Wykresy użycia |
| `app/facilities/` | Placówki i plany subskrypcji |
| `components/MedicalResultView.tsx` | Widok wyniku OCR z alertami |
| `lib/api.ts` | Klient HTTP (fetch wrapper + download helpers) |

### Baza danych

```sql
organizations  ──< users
organizations  ──< api_keys
api_keys       ──< scans
scans          contains: raw_text, parsed_json, doc_type, confidence
```

Schemat: [`init.sql`](../init.sql)

## Przepływ skanowania

```
1. Klient POST /v1/scan  (Bearer token, multipart/form-data)
2. API weryfikuje klucz → sprawdza limit skanów (Redis counter)
3. Obraz przekazywany do Surya OCR → raw text + bboxes
4. classifier.py → typ dokumentu (morphology / lab / discharge…)
5. parser.py → ekstrakcja parametrów (HGB, WBC, PESEL, daty…)
6. Wynik zapisywany w PostgreSQL (scans)
7. Response JSON z parsed_data + alerts
```

## Środowiska

| Środowisko | URL | Gałąź |
|-----------|-----|--------|
| Development | `localhost:3000` / `localhost:8000` | `main` / feature branch |
| Production (SaaS) | `panel.ikzocr.pl` / `api.ikzocr.pl` | `main` (Watchtower auto-deploy) |
| On-Premise | Infrastruktura klienta | Tagged release |

## Skalowanie

- **OCR API** — bezstanowy, skaluje poziomo (dodaj repliki za load balancerem)
- **Surya** — GPU opcjonalnie (CPU domyślnie); model ładuje się raz przy starcie
- **PostgreSQL** — primary + read replica dla Enterprise
- **Redis** — single instance dla SaaS; Redis Cluster dla Enterprise

## Zależności zewnętrzne

| Biblioteka | Wersja | Cel |
|-----------|--------|-----|
| surya-ocr | 0.6.x | Silnik OCR (wykrywanie tekstu, layout) |
| fastapi | 0.111+ | Framework HTTP |
| asyncpg | 0.29+ | Klient PostgreSQL async |
| pydantic | 2.x | Walidacja danych |
| pillow | 10.x | Przetwarzanie obrazów |
| next | 14.x | Panel frontendowy |
| tailwindcss | 3.x | Style CSS |
