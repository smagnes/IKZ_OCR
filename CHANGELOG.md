# Changelog

Wszystkie istotne zmiany w projekcie IKZOCR są dokumentowane w tym pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.3.0] — 2026-07-27

### Dodano
- Eksport wyników OCR do formatów `.txt`, `.md`, `.csv` (API: `/v1/documents/{id}/export.*`)
- Przyciski pobierania plików w panelu webowym (per dokument)
- Endpoint zbiorczy eksportu dokumentów (`/v1/documents/export`, `/v1/documents/export.md`)
- Dokumentacja: `docs/PRICING.md`, `docs/DEPLOYMENT.md`, `docs/API.md`, `docs/DEVELOPER.md`
- Dokumentacja: `docs/BETA_PROGRAM.md`, `docs/MARKETING_BRIEF.md`
- Dokumentacja prawna: RODO, NIS2, polityka prywatności, regulamin, retencja danych
- Licencja komercyjna (proprietary)
- Kwestionariusz wdrożeniowy dla administratorów On-Premise (PDF)

### Naprawiono
- Ekstrakcja morfologii dla Szpitala Powiatowego Iława: HCT missing (błędna granica `lo_min` w `_REF_CHAR` dla RDW-SD)
- Błędne wartości HGB=14.1 i WBC=8.9 — poprawiono kolejność przetwarzania parametrów
- Ekstrakcja imienia pacjenta: regex `_IMIE_ONLY_RE` pobierał dane z sąsiedniej kolumny
- FastAPI: kolizja trasy `/v1/documents/export` z `/{scan_id}` (statyczne trasy przeniesione przed dynamiczne)

---

## [0.2.0] — 2026-06-30

### Dodano
- Panel webowy (Next.js) dostępny pod `panel.ikzocr.pl`
- Zarządzanie kluczami API w panelu
- Historia skanowań z filtrowaniem
- Widok szczegółowy wyniku OCR (`MedicalResultView`)
- Obsługa planów subskrypcji: Starter (200), Pro (1000), Enterprise (5000)
- Limity skanów per klucz API

### Zmieniono
- Silnik OCR zaktualizowany do Surya 0.6.x
- Poprawa ekstrakcji morfologii: obsługa wielokolumnowych wyników laboratoryjnych
- Maskowanie PESEL w bazie danych (`XXXXXX*****`)

---

## [0.1.0] — 2026-05-01

### Dodano
- Bazowa architektura: FastAPI + Surya OCR + PostgreSQL + Redis
- Obsługa typów dokumentów: morfologia, wyniki szpitalne, zwolnienia lekarskie
- API endpoint `POST /v1/scan` — przesyłanie i analiza dokumentów
- API endpoint `GET /v1/documents` — lista wyników
- Uwierzytelnianie przez klucze API (Bearer token)
- Docker Compose: `ocr-api`, `panel`, `postgres`, `redis`
- Watchtower — automatyczne aktualizacje obrazów Docker

---

## Planowane (Roadmap)

- [ ] Webhook — powiadomienia o zakończeniu skanowania
- [ ] Integracja z HIS (HL7 FHIR)
- [ ] Obsługa dokumentów wielostronicowych (batch)
- [ ] Dashboard analityczny (statystyki skanowań)
- [ ] Audit trail — logi operacji dla RODO
- [ ] SMTP — wysyłka powiadomień email
- [ ] Audyt zewnętrzny bezpieczeństwa (NIS2, Q4 2026)
