# IKZOCR API — Dokumentacja

**Base URL:** `https://api.ikzocr.pl` (SaaS) lub `http://twoj-serwer:8000` (On-Premise)  
**Wersja API:** v1  
**Autoryzacja:** `Authorization: Bearer <klucz_api>`

---

## Skanowanie dokumentu

### `POST /v1/scan`

Przesyła plik (obraz lub PDF) do OCR. Obsługuje JPG, PNG, PDF (do 20 MB).

**Nagłówki:**
```
Authorization: Bearer mk_xxxxx
Content-Type: multipart/form-data
```

**Parametry (form-data):**
| Pole | Typ | Opis |
|------|-----|------|
| `file` | File | Obraz JPG/PNG lub PDF |

**Przykład:**
```bash
curl -X POST https://api.ikzocr.pl/v1/scan \
  -H "Authorization: Bearer mk_xxxxx" \
  -F "file=@wynik_morfologii.jpg"
```

**Odpowiedź (200 OK):**
```json
{
  "scan_id": "6e5ebe2f-aa2f-4e86-850b-e140cb90e7bd",
  "status": "ok",
  "doc_type": "morfologia",
  "doc_type_label": "Morfologia krwi",
  "confidence": {
    "text": 0.97,
    "values": 0.92,
    "units": 0.88,
    "overall": 0.92
  },
  "patient": "ANNA KOWALSKA",
  "pesel_masked": "8001**12345",
  "doctor": "lek. med. Jan Nowak",
  "facility": "Szpital Powiatowy w Iławie",
  "exam_date": "17-10-2024",
  "fields": {
    "HGB": "12.5",
    "WBC": "4.17",
    "RBC": "4.1",
    "PLT": "270",
    "HCT": "38.9",
    "MCV": "93.3",
    "MCH": "30.0",
    "MCHC": "32.1 ↓"
  },
  "alerts": [],
  "raw_text": "Powiatowy Szpital...",
  "processing_time_ms": 4230
}
```

---

## Dokumenty (archiwum)

### `GET /v1/documents`

Lista skanów (paginacja).

**Parametry query:**
| Parametr | Domyślnie | Opis |
|----------|-----------|------|
| `page` | 1 | Numer strony |
| `limit` | 20 (max 100) | Wyników na stronę |
| `doc_type` | — | Filtr: `morfologia`, `recepta`, `wynik_laboratoryjny`, `ekg`, `skierowanie`, `rtg_usg`, `karta_informacyjna`, `epikryza` |

```bash
curl "https://api.ikzocr.pl/v1/documents?page=1&limit=10&doc_type=morfologia" \
  -H "Authorization: Bearer mk_xxxxx"
```

---

### `GET /v1/documents/{scan_id}`

Szczegóły pojedynczego skanu.

---

### `DELETE /v1/documents/{scan_id}`

Usuwa skan z bazy danych (nieodwracalne).

---

## Eksport

### `GET /v1/documents/export`

Eksport wszystkich skanów do **CSV**.

```bash
curl "https://api.ikzocr.pl/v1/documents/export" \
  -H "Authorization: Bearer mk_xxxxx" \
  -o eksport.csv
```

### `GET /v1/documents/export.md`

Eksport wszystkich skanów do **Markdown**.

### `GET /v1/documents/{scan_id}/export.txt`

Eksport pojedynczego skanu do **TXT**.

### `GET /v1/documents/{scan_id}/export.md`

Eksport pojedynczego skanu do **Markdown**.

### `GET /v1/documents/{scan_id}/export.csv`

Eksport pojedynczego skanu do **CSV**.

---

## Statystyki

### `GET /v1/stats`

Statystyki konta (liczba skanów, typy, pewność, czas przetwarzania).

---

## Klucze API

### `GET /v1/api-keys`

Lista kluczy API przypisanych do konta.

### `POST /v1/api-keys`

Tworzy nowy klucz API (plan Pro/Enterprise).

```json
{
  "name": "Poradnia Kardiologiczna",
  "facility_name": "Centrum Medyczne XYZ"
}
```

### `PATCH /v1/api-keys/{key_id}/webhook`

Ustawia URL webhooka — system wyśle wynik OCR na podany adres po każdym skanie.

```json
{
  "webhook_url": "https://twojsystem.pl/webhook/ocr"
}
```

**Payload webhooka** (POST na Twój URL):
```json
{
  "event": "scan.completed",
  "scan_id": "...",
  "doc_type": "morfologia",
  "patient": "...",
  "fields": {...},
  "alerts": [...]
}
```

---

## Kody błędów

| Kod | Znaczenie |
|-----|-----------|
| 400 | Nieprawidłowy plik lub brakujące parametry |
| 401 | Brak lub nieprawidłowy klucz API |
| 403 | Przekroczony limit planu |
| 404 | Skan nie istnieje |
| 413 | Plik za duży (max 20 MB) |
| 429 | Za dużo żądań (rate limit) |
| 500 | Błąd serwera OCR |

---

## Limity

| Plan | Skanów/miesiąc | Max rozmiar pliku | Rate limit |
|------|---------------|-------------------|------------|
| Starter | 200 | 10 MB | 10 req/min |
| Pro | 1 000 | 20 MB | 60 req/min |
| Enterprise | 5 000+ | 50 MB | 300 req/min |

---

## Typy dokumentów

| `doc_type` | Opis | Ekstrahowane pola |
|------------|------|-------------------|
| `morfologia` | Morfologia krwi | HGB, WBC, RBC, PLT, HCT, MCV, MCH, MCHC, PCT, MPV, PDW, RDW-CV, RDW-SD, P-LCR |
| `wynik_laboratoryjny` | Wynik lab. (biochemia) | Glukoza, Kreatynina, Cholesterol, TSH, FT4, ALT, AST, CRP, APTT i inne |
| `recepta` | Recepta | Leki, dawkowanie, odpłatność |
| `skierowanie` | Skierowanie | Cel, diagnoza wstępna |
| `ekg` | EKG | Opis, rytm |
| `rtg_usg` | Badanie obrazowe | Opis |
| `karta_informacyjna` | Karta szpitalna | Rozpoznania, leki, zabiegi, zwolnienie |
| `epikryza` | Epikryza | Przebieg, rozpoznanie końcowe |
