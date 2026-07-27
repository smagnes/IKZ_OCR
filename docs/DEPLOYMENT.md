# IKZOCR — Przewodnik wdrożeniowy (DevOps)

## Wymagania systemowe

| Komponent | Minimum | Zalecane |
|-----------|---------|---------|
| CPU | 4 rdzenie x86_64 | 8+ rdzeni |
| RAM | 8 GB | 16–32 GB |
| Dysk | 50 GB SSD | 200 GB NVMe |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Docker Engine | 24.0+ | latest |
| Docker Compose | 2.20+ | latest |

---

## Instalacja (pierwsza konfiguracja)

### 1. Zainstaluj Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Pobierz aplikację

```bash
git clone https://github.com/TWOJA_ORG/ikzocr.git
cd ikzocr
```

### 3. Konfiguracja środowiska

```bash
cp api/.env.example api/.env
```

Edytuj `api/.env`:

```env
# Baza danych (zmień hasło!)
POSTGRES_USER=ikzocr
POSTGRES_PASSWORD=ZMIEN_TO_HASLO
POSTGRES_DB=ikzocr

# Bezpieczeństwo
SECRET_KEY=LOSOWY_STRING_MIN_32_ZNAKI
DEMO_KEY=OPCJONALNY_KLUCZ_DEMO

# Email (opcjonalne — do wysyłki wyników)
SMTP_HOST=smtp.twojadomena.pl
SMTP_PORT=587
SMTP_USER=ocr@twojadomena.pl
SMTP_PASS=HASLO_SMTP
EMAIL_FROM=ocr@twojadomena.pl

# Środowisko
ENVIRONMENT=production
```

### 4. Uruchom

```bash
docker compose up -d
```

Pierwsze uruchomienie pobiera modele Surya OCR (~2 min, wymaga internetu).

### 5. Weryfikacja

```bash
# Sprawdź status kontenerów
docker compose ps

# Sprawdź logi API
docker compose logs -f ocr-api

# Test endpoint
curl http://localhost:8000/health
```

---

## Konfiguracja HTTPS (Nginx + Let's Encrypt)

### Nginx reverse proxy

```nginx
server {
    listen 80;
    server_name panel.twojadomena.pl;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name panel.twojadomena.pl;

    ssl_certificate     /etc/letsencrypt/live/panel.twojadomena.pl/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/panel.twojadomena.pl/privkey.pem;

    # Panel Next.js
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API FastAPI
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        client_max_body_size 20M;
    }
}
```

```bash
# Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d panel.twojadomena.pl
```

---

## Aktualizacje (bez utraty danych)

### Automatyczne (Watchtower) — zalecane

```yaml
# Dodaj do docker-compose.yml
watchtower:
  image: containrrr/watchtower
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  command: --interval 3600 --cleanup
  restart: unless-stopped
```

Watchtower co godzinę sprawdza Docker Hub pod kątem nowych obrazów i aktualizuje kontenery. **Dane w PostgreSQL nie są dotykane.**

### Ręczne

```bash
docker compose pull
docker compose up -d --no-deps ocr-api panel
```

---

## Backup bazy danych

### Automatyczny backup (cron)

```bash
# /etc/cron.d/ikzocr-backup
0 2 * * * root docker exec medyk_db pg_dump -U ikzocr ikzocr | gzip > /backups/ikzocr_$(date +\%Y\%m\%d).sql.gz
```

### Przywracanie

```bash
gunzip -c /backups/ikzocr_20260101.sql.gz | docker exec -i medyk_db psql -U ikzocr ikzocr
```

### Retencja backupów

```bash
# Usuń backupy starsze niż 30 dni
find /backups -name "ikzocr_*.sql.gz" -mtime +30 -delete
```

---

## Monitoring

### Health check

```bash
# API
curl http://localhost:8000/health

# Odpowiedź OK:
{"status":"ok","db":"connected","ocr":"ready"}
```

### Logi

```bash
# Live logi API
docker compose logs -f ocr-api

# Ostatnie 100 linii panelu
docker compose logs --tail=100 panel
```

### Metryki (Prometheus + Grafana)

- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (admin / patrz `.env`)

---

## Bezpieczeństwo

### Firewall (UFW)

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # API — tylko przez Nginx
sudo ufw deny 5432/tcp   # PostgreSQL — tylko lokalnie
sudo ufw enable
```

### Rotacja kluczy API

Klucze API klientów można unieważnić przez panel admina lub bezpośrednio w bazie:

```sql
UPDATE api_keys SET is_active = false WHERE key_prefix = 'mk_xxx';
```

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---------|-------------|
| API nie odpowiada | `docker compose restart ocr-api` |
| OCR zwraca błąd | Sprawdź RAM: `free -h` (min. 6 GB wolne) |
| Baza niedostępna | `docker compose restart db` |
| Brak miejsca na dysku | `docker system prune -f` |
| Modele nie ładują | `docker compose logs ocr-api \| grep -i surya` |

---

## Kontakt wsparcia

📧 devops@ikzocr.pl  
🔑 SSH dostęp read-only (na żądanie, za zgodą klienta)
