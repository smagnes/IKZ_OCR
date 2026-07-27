# IKZOCR — Platforma OCR dla dokumentów medycznych

Pierwsze w Polsce rozwiązanie AI do automatycznego rozpoznawania i strukturyzowania danych z dokumentów medycznych.

> **Wersja:** 0.3.0 · [Changelog](CHANGELOG.md) · [Licencja](LICENSE)

## Dokumentacja

| Dokument | Opis |
|----------|------|
| [docs/PRICING.md](docs/PRICING.md) | Plany subskrypcji, cennik, limity skanów |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Instalacja On-Premise krok po kroku |
| [docs/API.md](docs/API.md) | Referencja API (wszystkie endpointy) |
| [docs/DEVELOPER.md](docs/DEVELOPER.md) | Architektura, dev setup, dodawanie nowych typów dokumentów |
| [docs/BETA_PROGRAM.md](docs/BETA_PROGRAM.md) | Program beta — wymagania, korzyści, timeline |
| [docs/MARKETING_BRIEF.md](docs/MARKETING_BRIEF.md) | Pozycjonowanie, segmenty klientów, key messages |
| [docs/legal/RODO.md](docs/legal/RODO.md) | Polityka ochrony danych osobowych |
| [docs/legal/NIS2_COMPLIANCE.md](docs/legal/NIS2_COMPLIANCE.md) | Zgodność z dyrektywą NIS2 |
| [docs/legal/PRIVACY_POLICY.md](docs/legal/PRIVACY_POLICY.md) | Polityka prywatności |
| [docs/legal/TERMS_OF_SERVICE.md](docs/legal/TERMS_OF_SERVICE.md) | Regulamin świadczenia usług |
| [docs/legal/DATA_RETENTION.md](docs/legal/DATA_RETENTION.md) | Polityka retencji i usuwania danych |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architektura systemu — diagram i opis komponentów |
| [docs/SECURITY_POLICY.md](docs/SECURITY_POLICY.md) | Polityka bezpieczeństwa (TLS, auth, podatności, disclosure) |
| [docs/SLA.md](docs/SLA.md) | Umowa o poziomie usług — dostępność, czasy odpowiedzi, kompensaty |
| [docs/INCIDENT_RESPONSE.md](docs/INCIDENT_RESPONSE.md) | Polityka obsługi incydentów i breachów danych |
| [docs/FAQ.md](docs/FAQ.md) | Najczęściej zadawane pytania |
| [docs/ONBOARDING.md](docs/ONBOARDING.md) | Pierwsze kroki — SaaS, On-Premise, API |
| [docs/UPGRADE_GUIDE.md](docs/UPGRADE_GUIDE.md) | Aktualizacja systemu On-Premise |
| [docs/INTEGRATIONS.md](docs/INTEGRATIONS.md) | Integracje z HIS/LIS, webhook, przykłady kodu |
| [docs/IKZOCR.postman_collection.json](docs/IKZOCR.postman_collection.json) | Kolekcja Postman do testowania API |

## Komponenty

| Serwis | Port | Opis |
|--------|------|------|
| `ocr-api` | 8000 | FastAPI — serwer OCR (Surya AI) |
| `panel` | 3000 | Next.js — panel zarządzania |
| `postgres` | 5432 | Baza danych (PostgreSQL 18) |
| `redis` | 6379 | Cache i sesje |
| `nats` | 4222 | Message broker |
| `prometheus` | 9090 | Metryki |
| `grafana` | 3001 | Dashboard monitoringu (admin/medyk2026) |

## Szybki start

```bash
# 1. Zaloguj się do rejestru
docker login ikz-gl.ib2.eu:5050 -u magnessebastian@gmail.com

# 2. Skopiuj konfigurację
cp api/.env.example api/.env
# Edytuj api/.env — ustaw swoje klucze API

# 3. Uruchom wszystko
docker compose up -d

# 4. Sprawdź logi OCR API (pierwsze uruchomienie ładuje modele ~2 min)
docker compose logs -f ocr-api

# 5. Otwórz panel
open http://localhost:3000

# 6. Przetestuj API
curl -X POST http://localhost:8000/v1/scan \
  -H "Authorization: Bearer mk_prod_demo123" \
  -F "file=@twoj_wynik.jpg"
```

## Integracja z IKZ Mobile

W aplikacji Flutter zmień use case `send_document_to_ocr`:

```dart
// lib/src/repositories/ocr_scanner/data/datasources/ocr_remote_datasource.dart
final response = await dio.post(
  'http://twoj-serwer:8000/v1/scan',
  data: formData,
  options: Options(headers: {
    'Authorization': 'Bearer $apiKey',
    'X-IKZ-Silos-Id': silosId,  // ← automatycznie zapisuje wynik do silosu
  }),
);
```

## Struktura projektu

```
medyk-ocr/
├── api/                    # FastAPI backend
│   ├── main.py            # Główna aplikacja + endpointy
│   ├── schemas.py         # Modele danych (Pydantic)
│   ├── ocr/
│   │   ├── processor.py   # Wrapper na Surya OCR
│   │   ├── classifier.py  # Wykrywanie typu dokumentu
│   │   └── parser.py      # Ekstrakcja danych (HGB, WBC, PESEL...)
│   └── Dockerfile
├── panel/                  # Next.js panel
│   └── src/app/
│       ├── scan/          # Skanowanie dokumentów
│       ├── documents/     # Archiwum
│       ├── statistics/    # Wykresy i statystyki
│       ├── api-keys/      # Zarządzanie API
│       └── facilities/    # Placówki i plany
├── monitoring/
│   ├── prometheus.yml
│   └── grafana/
├── init.sql               # Schemat bazy danych
└── docker-compose.yml
```

## Obsługiwane typy dokumentów

- Morfologia krwi (HGB, WBC, RBC, PLT, HCT, MCV, MCH, MCHC)
- Wyniki laboratoryjne (glukoza, kreatynina, cholesterol, TSH, FT4, ALT, AST)
- Recepty (leki, dawkowanie, refundacja)
- Skierowania
- EKG
- Badania obrazowe (RTG, USG, TK, MR)
- Epikryzy i karty informacyjne leczenia szpitalnego

## Alerty medyczne (auto-wykrywane)

- Anemia (HGB < 11.5 g/dL)
- Leukocytoza (WBC > 11.0)
- Hiperglikemia (glukoza > 126 mg/dL)
- Hipoglikemia (glukoza < 70 mg/dL)
- Niedoczynność tarczycy (TSH > 4.5)
- Nadczynność tarczycy (TSH < 0.4)
