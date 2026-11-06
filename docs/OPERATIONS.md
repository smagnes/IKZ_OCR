# IKZOCR — Dokumentacja operacyjna

## Architektura produkcyjna

```
internet → nginx (SSL) → docker: medyk_ocr_api (:8000) + medyk_panel (:3000)
                       → PostgreSQL (Supabase, eu-central-1)
                       → Redis (kontener medyk_redis)
```

**Serwer:** GCP VM `instance-20261012-073859`, IP `34.41.15.71`  
**SSH:** `ssh smgraphic4u@34.41.15.71`  
**App dir:** `~/ikzocr`

---

## Kontenery

| Kontener | Obraz | Port | Opis |
|---|---|---|---|
| `medyk_ocr_api` | `medyk-ocr-api:latest` | 8000 | FastAPI + OCR (Claude API) |
| `medyk_panel` | `medyk-ocr-panel:latest` | 3000 | Next.js frontend |
| `medyk_redis` | `redis:7-alpine` | 6379 | Cache + rate limiting |

### Restart kontenera API
```bash
cd ~/ikzocr
docker stop medyk_ocr_api && docker rm medyk_ocr_api
docker run -d --name medyk_ocr_api --env-file ./api/.env \
  --restart unless-stopped --network ikzocr_medyk_net \
  -p 8000:8000 medyk-ocr-api:latest
```

### Sprawdzenie statusu
```bash
docker ps
curl http://localhost:8000/health
docker logs medyk_ocr_api --tail=50
```

---

## Deploy (aktualizacja kodu)

```bash
cd ~/ikzocr
git fetch origin && git reset --hard origin/main

# Rebuild API (tylko jeśli zmieniły się pliki Python lub Dockerfile)
docker build -t medyk-ocr-api:latest ./api
docker stop medyk_ocr_api && docker rm medyk_ocr_api
docker run -d --name medyk_ocr_api --env-file ./api/.env \
  --restart unless-stopped --network ikzocr_medyk_net \
  -p 8000:8000 medyk-ocr-api:latest

# Rebuild Panel (tylko jeśli zmieniły się pliki panel/)
docker build -t medyk-ocr-panel:latest ./panel
docker restart medyk_panel
```

---

## OCR — zasady KTÓRYCH NIE WOLNO ZMIENIAĆ

**Backend OCR = wyłącznie Claude API (`claude-haiku-4-5-20251001`)**

- `OCR_ENGINE=claude` jest hardcoded w Dockerfile — nie zmieniać
- `surya-ocr`, `torch`, `torchvision`, `paddleocr` są USUNIĘTE z requirements.txt — nie dodawać
- `llama.cpp` jest USUNIĘTY z Dockerfile — nie dodawać
- Poprzednie zmiany backendu na Surya złamały produkcję (11.2026)

Jeśli ktoś (włącznie z Claude) sugeruje zmianę backendu OCR — najpierw konsultacja z właścicielem.

---

## Zmienne środowiskowe (`~/ikzocr/api/.env`)

```
DATABASE_URL=postgresql://...supabase...
REDIS_URL=redis://redis:6379
CORS_ORIGINS=http://localhost:3000,https://panel.ikzocr.pl
ANTHROPIC_API_KEY=sk-ant-...        # wymagany, bez niego OCR nie działa
JWT_SECRET=...                       # do zmiany na produkcji
PRELOAD_MODELS=false                 # false = nie ładuj modeli ML przy starcie
OCR_ENGINE=claude                    # hardcoded w Dockerfile, ale też tu dla pewności
```

---

## Maintenance page

Gdy API lub Panel nie odpowiada, nginx automatycznie serwuje stronę przerwy technicznej.

- **Plik HTML:** `~/www/maintenance.html`
- **Triggeruje:** błędy 502, 503, 504 z backendu

---

## Health check i alerty

**Skrypt:** `~/ikzocr-health-check.sh`  
**Cron:** co 2 minuty  
**Log:** `~/ikzocr-health.log`

```bash
# Sprawdź log alertów
tail -50 ~/ikzocr-health.log

# Uruchom ręcznie
~/ikzocr-health-check.sh

# Sprawdź cron
crontab -l
```

> **TODO alerty email:** Skrypt loguje awarie do pliku. Żeby wysyłał maile:
> - Opcja A: Skonfiguruj webhook n8n (workflow "IKZOCR Alert") i dodaj `curl -X POST https://n8n.../webhook/ikzocr-alert -d "{\"service\":\"$name\"}"` do skryptu
> - Opcja B: Zainstaluj `msmtp` i skonfiguruj Gmail SMTP

---

## Demo isolation

Każdy gość dostaje tymczasowe konto (24h, 10 skanów):

- `POST /auth/demo` — tworzy konto i klucz API
- `POST /auth/demo/end` — usuwa sesję i dokumenty natychmiast
- Sprzątanie wygasłych kont: przy starcie API + co 15 min
- Blokady w trybie demo: email, IKZ Mobile, webhooks, tworzenie kluczy API
- Rate limiting: per IP (okno przesuwne, in-memory)

Szczegóły: `docs/DEMO_ISOLATION.md`

---

## Bezpieczeństwo — braki do uzupełnienia

| # | Problem | Ryzyko | Fix |
|---|---|---|---|
| 1 | `JWT_SECRET=ikzocr_jwt_secret_change_in_production_2026` | Wysoki — każdy może sfałszować token | Zmień na losowy 64-znakowy string: `openssl rand -hex 32` |
| 2 | Brak rotacji kluczy API Anthropic | Średni — klucz wyciekł do `.env` bez backupu | Ustaw alert wygaśnięcia w Anthropic Console |
| 3 | Alerty email nie działają | Średni — awaria niezauważona | Skonfiguruj n8n webhook lub msmtp |
| 4 | Dysk 10GB na GCP | Niski-Średni — build może zapełnić dysk | Zwiększ do 20-30GB lub dodaj cron `docker system prune -f` raz/tydzień |
| 5 | Panel Next.js budowany jako dev? | Sprawdź | `docker exec medyk_panel node -e "console.log(process.env.NODE_ENV)"` |
| 6 | Brak backupu Supabase | Wysoki | Włącz Point-in-Time Recovery w Supabase Dashboard |
| 7 | `CORS_ORIGINS` zawiera `localhost:3000` | Niski | Usuń localhost z CORS na produkcji |

---

## Dysk — zarządzanie miejscem

```bash
# Sprawdź zajętość
df -h /

# Wyczyść nieużywane obrazy Docker (bezpiecznie)
docker system prune -f

# Cron czyszczenia (zalecane raz/tydzień, niedziela 3:00)
# Dodaj do crontab: 0 3 * * 0 docker system prune -f >> ~/docker-prune.log 2>&1
```

Obraz `medyk-ocr-api:latest` po usunięciu surya/torch: **~470MB** (poprzednio 2.3GB).
