# Gemini prompt — nowa GCP VM dla IKZOCR v2

Wklej poniższy prompt do Gemini (najlepiej 1.5 Pro lub 2.0) w Google Cloud Console lub AI Studio.

---

## PROMPT DO GEMINI

```
Jestem programistą i chcę postawić nową VM na Google Cloud Platform (GCP) dla projektu IKZOCR v2.
Pomóż mi przejść przez cały proces krok po kroku, wydając dokładne komendy gcloud CLI.

## Kontekst projektu

To jest testowa VM dla lokalnego silnika OCR do dokumentów medycznych.
- Nie dotykamy istniejącej produkcji na 34.41.15.71
- Nowa VM ma mieć inny IP i działać niezależnie
- Na VM będzie działał Docker Compose z: FastAPI (port 8000), Next.js panel (port 3000), Redis, NATS, Prometheus, Grafana
- OCR działa lokalnie (PaddleOCR) — NIE używamy zewnętrznych API
- Dostęp: SSH + otwarte porty 8000 i 3000 dla integracji z zewnętrzną aplikacją

## Wymagania VM

- Typ maszyny: e2-standard-4 (4 vCPU, 16GB RAM) — PaddleOCR potrzebuje RAM
- OS: Ubuntu 22.04 LTS
- Dysk: 50GB SSD (modele PaddleOCR ~2GB, Helsinki-NLP ~300MB)
- Region: europe-central2 (Warszawa) — dane medyczne, RODO
- Firewall: porty 22 (SSH), 8000 (API), 3000 (panel), 3001 (Grafana)
- Static external IP (żebyśmy mieli stały adres do testów)

## Kroki do wykonania

1. Utwórz nową VM z podanymi parametrami (podaj dokładne komendy gcloud)
2. Skonfiguruj firewall rules dla portów 8000, 3000, 3001
3. Zarezerwuj static external IP i przypisz do VM
4. SSH na VM i zainstaluj: Docker, Docker Compose, git
5. Sklonuj repo: https://github.com/smagnes/IKZ_OCR.git
6. Skonfiguruj plik api/.env (podaj template z placeholderami — BEZ prawdziwych kluczy)
7. Uruchom: docker compose -f docker-compose.v2.yml up -d --build
8. Zweryfikuj że api odpowiada na http://[VM_IP]:8000/health
9. Zweryfikuj że panel działa na http://[VM_IP]:3000

Użyj projektu GCP: [TWÓJ_PROJEKT_GCP]
Podaj mi każdą komendę osobno żebym mógł ją skopiować i wkleić do terminala.
Zaznacz gdzie muszę podać własne wartości (projekt, klucze).
```

---

## Uzupełnij przed wklejeniem

Przed wklejeniem do Gemini podmień:
- `[TWÓJ_PROJEKT_GCP]` → nazwa twojego projektu GCP (np. `ikzocr-prod-2024`)

## Czego Gemini NIE robi za Ciebie

- Nie pyta o klucze API (podasz je ręcznie do `api/.env` po SSH)
- Nie konfiguruje DNS (domena ikzocr.pl zostaje na produkcji)
- Nie dotyka produkcyjnego VM 34.41.15.71

## Po postawieniu VM — plik api/.env na nowej maszynie

```env
ANTHROPIC_API_KEY=sk-ant-...   # opcjonalnie, silnik=paddle więc nieużywany
OCR_ENGINE=paddle
API_KEY=mk_test_v2_keepit
REDIS_URL=redis://redis:6379
NATS_URL=nats://nats:4222
```

## Integracja z keepithealthy.pl / Dr Kiwi

Po uruchomieniu VM:
1. Nowy adres API: `http://[NOWY_VM_IP]:8000`
2. Endpoint do testów OCR bez Claude: `POST /v1/scan/local`
3. Endpoint tłumaczenia: `POST /v1/translate/local`
4. Auth header: `X-API-Key: mk_test_v2_keepit`

Przykładowy curl test:
```bash
curl -X POST http://[NOWY_VM_IP]:8000/v1/scan/local \
  -H "X-API-Key: mk_test_v2_keepit" \
  -F "file=@dokument_medyczny.pdf"
```
