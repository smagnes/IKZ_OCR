# IKZOCR — Przewodnik aktualizacji

> Dotyczy instalacji On-Premise. W wersji SaaS aktualizacje są automatyczne po stronie SZOP sp. z o.o.

## Spis treści

1. [Zasady ogólne](#1-zasady-ogólne)
2. [Automatyczna aktualizacja (Watchtower)](#2-automatyczna-aktualizacja-watchtower)
3. [Ręczna aktualizacja](#3-ręczna-aktualizacja)
4. [Aktualizacja z migracją bazy danych](#4-aktualizacja-z-migracją-bazy-danych)
5. [Rollback do poprzedniej wersji](#5-rollback-do-poprzedniej-wersji)
6. [Historia wersji i zmiany wymagające działania](#6-historia-wersji-i-zmiany-wymagające-działania)
7. [Weryfikacja po aktualizacji](#7-weryfikacja-po-aktualizacji)

---

## 1. Zasady ogólne

**Dane są bezpieczne podczas aktualizacji.** Baza danych PostgreSQL i pliki konfiguracyjne przechowywane są w Docker volumes — aktualizacja obrazów kontenerów nie dotyka volumów.

Przed każdą aktualizacją:
```
□ Wykonaj backup bazy danych
□ Sprawdź CHANGELOG.md pod kątem breaking changes
□ Zaplanuj okno aktualizacji (może być krótki restart ~30s)
```

---

## 2. Automatyczna aktualizacja (Watchtower)

Watchtower sprawdza Docker Hub co 24h i automatycznie aktualizuje kontenery gdy dostępny jest nowy obraz.

### Konfiguracja Watchtower

```yaml
# docker-compose.yml — dodaj jeśli nie ma
watchtower:
    image: containrrr/watchtower
    container_name: ikzocr_watchtower
    volumes:
        - /var/run/docker.sock:/var/run/docker.sock
    environment:
        WATCHTOWER_POLL_INTERVAL: "86400"        # sprawdzaj co 24h
        WATCHTOWER_CLEANUP: "true"               # usuń stare obrazy
        WATCHTOWER_INCLUDE_STOPPED: "false"
        WATCHTOWER_LABEL_ENABLE: "false"         # aktualizuj wszystkie kontenery
        WATCHTOWER_NOTIFICATIONS: "email"
        WATCHTOWER_NOTIFICATION_EMAIL_FROM: "watchtower@ikzocr.pl"
        WATCHTOWER_NOTIFICATION_EMAIL_TO: "admin@twoja-placowka.pl"
        WATCHTOWER_NOTIFICATION_EMAIL_SERVER: "smtp.twoja-placowka.pl"
        WATCHTOWER_NOTIFICATION_EMAIL_SERVER_PORT: "587"
    restart: unless-stopped
```

```bash
# Uruchom / zaktualizuj Watchtower
docker compose up -d watchtower

# Sprawdź logi Watchtower
docker compose logs watchtower --since 24h
```

### Wymuszenie sprawdzenia teraz

```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --run-once \
  ikzocr_ocr-api ikzocr_panel
```

### Wyłączenie Watchtower (ręczne zarządzanie)

```yaml
# W docker-compose.yml usuń lub zakomentuj sekcję watchtower
# lub:
docker compose stop watchtower
docker compose rm watchtower
```

---

## 3. Ręczna aktualizacja

Standardowa procedura dla większości aktualizacji (bez zmian schematu bazy):

### Krok 1 — Backup bazy danych

```bash
# Zawsze rób backup przed aktualizacją
BACKUP_FILE="/opt/ikzocr/backups/pre-update-$(date +%Y%m%d-%H%M%S).sql"
mkdir -p /opt/ikzocr/backups

docker compose exec -T postgres pg_dump -U medyk medykocr > "$BACKUP_FILE"
gzip "$BACKUP_FILE"

echo "Backup zapisany: ${BACKUP_FILE}.gz"
ls -lh "${BACKUP_FILE}.gz"
```

### Krok 2 — Sprawdź dostępne wersje

```bash
# Aktualna wersja
curl -s http://localhost:8000/health | python3 -m json.tool

# Dostępne tagi na Docker Hub
# (lub sprawdź CHANGELOG.md w repo)
```

### Krok 3 — Pobierz nowe obrazy

```bash
cd /opt/ikzocr

# Zaktualizuj kod (dla zmian konfiguracyjnych i dokumentacji)
git pull origin main

# Pobierz nowe obrazy Docker
docker compose pull
```

### Krok 4 — Zrestartuj serwisy

```bash
# Opcja A: restart wszystkiego naraz (~30s downtime)
docker compose up -d --force-recreate

# Opcja B: rolling restart (mniejszy downtime, dla środowisk z load balancerem)
docker compose up -d --no-deps --force-recreate ocr-api
sleep 15
curl http://localhost:8000/health   # sprawdź czy wystartował
docker compose up -d --no-deps --force-recreate panel
```

### Krok 5 — Weryfikacja

```bash
# API zdrowe?
curl http://localhost:8000/health

# Testowy skan
curl -X POST http://localhost:8000/v1/scan \
  -H "Authorization: Bearer mk_TwójKlucz" \
  -F "file=@/opt/ikzocr/test_doc.jpg"

# Logi
docker compose logs --since 5m ocr-api | grep -E "ERROR|WARNING|Models loaded"
```

---

## 4. Aktualizacja z migracją bazy danych

Gdy CHANGELOG.md zawiera wpis `⚠️ Wymagana migracja DB` — wykonaj poniższe kroki.

### Procedura

```bash
# 1. Zatrzymaj serwisy (żeby nie pisały do bazy podczas migracji)
docker compose stop ocr-api panel

# 2. Backup (obowiązkowy!)
docker compose exec -T postgres pg_dump -U medyk medykocr \
  | gzip > /opt/ikzocr/backups/pre-migration-$(date +%Y%m%d).sql.gz

# 3. Pobierz nowy kod i obrazy
git pull origin main
docker compose pull

# 4. Sprawdź czy jest plik migracji
ls docs/migrations/

# 5. Wykonaj migrację
docker compose exec postgres psql -U medyk -d medykocr \
  -f /migrations/V0_3_to_V0_4.sql

# 6. Uruchom serwisy
docker compose up -d
```

### Przykładowa migracja (docs/migrations/V0_3_to_V0_4.sql)

```sql
-- Przykład migracji z v0.3 do v0.4
-- Zawsze idempotentna (IF NOT EXISTS / IF EXISTS)

ALTER TABLE scans ADD COLUMN IF NOT EXISTS page_count INTEGER DEFAULT 1;
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS webhook_url TEXT;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_scans_confidence
    ON scans(confidence);

-- Zaktualizuj wersję schematu
INSERT INTO schema_versions (version, applied_at)
VALUES ('0.4.0', NOW())
ON CONFLICT (version) DO NOTHING;
```

---

## 5. Rollback do poprzedniej wersji

Jeśli aktualizacja spowodowała problemy:

### Rollback kodu i obrazów

```bash
# Sprawdź poprzedni commit
git log --oneline -5

# Wróć do poprzedniej wersji kodu
git checkout v0.2.0    # lub konkretny commit hash

# Wróć do poprzednich obrazów Docker (jeśli tagowane)
docker compose pull  # pobierze wersję z .env lub docker-compose.yml

# Lub ręcznie ustaw poprzedni tag w docker-compose.yml:
# image: szopai/ikzocr-api:0.2.0
docker compose up -d --force-recreate
```

### Rollback bazy danych

```bash
# Przywróć z backupu sprzed aktualizacji
BACKUP_FILE="/opt/ikzocr/backups/pre-update-20260727-103000.sql.gz"

# Zatrzymaj serwisy
docker compose stop ocr-api panel

# Przywróć bazę
gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres \
  psql -U medyk -d medykocr

# Uruchom poprzednią wersję
docker compose up -d
```

---

## 6. Historia wersji i zmiany wymagające działania

### v0.3.0 → aktualna

Brak zmian schematu bazy. Standardowa aktualizacja.

**Nowe zmienne środowiskowe (opcjonalne):**
```env
# Brak nowych wymaganych zmiennych w v0.3.0
```

### v0.2.0 → v0.3.0

Brak migracji bazy. Nowe endpointy eksportu.

**Sprawdź czy CORS_ORIGINS zawiera URL panelu:**
```env
CORS_ORIGINS=https://panel.twoja-domena.pl,http://localhost:3000
```

### v0.1.0 → v0.2.0

Zmiana schematu: dodanie tabeli `organizations` i kolumny `org_id` w `api_keys`.

```sql
-- Migracja v0.1.0 → v0.2.0
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS org_id UUID;
CREATE TABLE IF NOT EXISTS organizations (...);
```

---

## 7. Weryfikacja po aktualizacji

Po każdej aktualizacji wykonaj poniższy checklist:

```bash
# 1. Health check API
curl http://localhost:8000/health
# Oczekiwane: {"status":"ok","version":"X.Y.Z"}

# 2. Zalogowanie w panelu
open http://localhost:3000
# Sprawdź: czy panel ładuje się, czy lista dokumentów działa

# 3. Testowy skan
curl -X POST http://localhost:8000/v1/scan \
  -H "Authorization: Bearer mk_TwójKlucz" \
  -F "file=@test_morfologia.jpg"
# Oczekiwane: 200 z parsed_data

# 4. Export działa
curl "http://localhost:8000/v1/documents/export" \
  -H "Authorization: Bearer mk_TwójKlucz"
# Oczekiwane: 200 CSV

# 5. Baza danych osiągalna
docker compose exec postgres psql -U medyk -d medykocr \
  -c "SELECT COUNT(*) FROM scans;"

# 6. Logi bez błędów przez 5 minut
docker compose logs --since 5m ocr-api | grep -c "ERROR"
# Oczekiwane: 0

# 7. Użycie zasobów normalne
docker stats --no-stream
# RAM ocr-api: < 8 GB, CPU po inicjalizacji: < 5%
```

Jeśli któryś krok zawiedzie — wróć do sekcji [Rollback](#5-rollback-do-poprzedniej-wersji).

---

## Wsparcie przy aktualizacji

Problemy z aktualizacją? Skontaktuj się z nami przed rollbackiem:

- Email: support@ikzocr.pl (z logami z `docker compose logs`)
- GitHub Issues: https://github.com/smagnes/IKZ_OCR/issues
- Klienci Enterprise: dedykowany kanał Slack z SLA 4h
