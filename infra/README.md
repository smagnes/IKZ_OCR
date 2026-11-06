# infra/ — konfiguracja serwera GCP

Kopia plików które żyją poza repo (na VM lub w nginx), żeby odtworzyć środowisko od zera.

## Pliki

| Plik | Lokalizacja na VM | Jak wgrać |
|------|------------------|-----------|
| `nginx-ikzocr.conf` | `/etc/nginx/sites-enabled/ikzocr` | `sudo cp nginx-ikzocr.conf /etc/nginx/sites-enabled/ikzocr && sudo nginx -t && sudo systemctl reload nginx` |
| `maintenance.html` | `~/www/maintenance.html` | `cp maintenance.html ~/www/` |
| `health-check.sh` | `~/ikzocr-health-check.sh` | `cp health-check.sh ~/ikzocr-health-check.sh && chmod +x ~/ikzocr-health-check.sh` |
| `crontab.txt` | crontab użytkownika | `crontab crontab.txt` |

## .env — NIE ma w repo

`~/ikzocr/api/.env` zawiera sekrety i **nie jest w git**. Przy odtwarzaniu środowiska tworzysz go ręcznie:

```
DATABASE_URL=postgresql://...supabase...
REDIS_URL=redis://redis:6379
CORS_ORIGINS=https://panel.ikzocr.pl
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET=<openssl rand -hex 32>
PRELOAD_MODELS=false
OCR_ENGINE=claude
```

Wartości są w sejfie / menedżerze haseł — nie w tym repo.

## Odtworzenie środowiska od zera

```bash
# 1. Klonuj repo
git clone https://github.com/smagnes/IKZ_OCR.git ~/ikzocr

# 2. Stwórz .env
nano ~/ikzocr/api/.env

# 3. Wgraj infra
sudo cp infra/nginx-ikzocr.conf /etc/nginx/sites-enabled/ikzocr
mkdir -p ~/www && cp infra/maintenance.html ~/www/
cp infra/health-check.sh ~/ikzocr-health-check.sh && chmod +x ~/ikzocr-health-check.sh
crontab infra/crontab.txt

# 4. Zainstaluj certbot i odtwórz certyfikaty TLS
sudo certbot --nginx -d api.ikzocr.pl -d panel.ikzocr.pl

# 5. Zbuduj i uruchom kontenery
cd ~/ikzocr
docker network create ikzocr_medyk_net
docker run -d --name medyk_redis --network ikzocr_medyk_net redis:7-alpine
docker build -t medyk_ocr_api:latest -f api/Dockerfile api/
docker run -d --name medyk_ocr_api --network ikzocr_medyk_net --env-file ./api/.env -p 8000:8000 medyk_ocr_api:latest
docker build -t medyk-ocr-panel:latest panel/
docker run -d --name medyk_panel --network ikzocr_medyk_net -p 3000:3000 medyk-ocr-panel:latest

# 6. Sprawdź
curl https://api.ikzocr.pl/health
```
