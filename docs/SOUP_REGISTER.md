# SOUP Register — IKZOCR Cloud

> Software of Unknown Provenance — rejestr zgodny z IEC 62304 §8.1.2  
> Ostatnia aktualizacja: 2026-11-15

| Biblioteka | Wersja | Licencja | Rola | Ryzyko | CVE-last-check | Uwagi |
|---|---|---|---|---|---|---|
| fastapi | 0.115.0 | MIT | Framework HTTP API | Niskie | 2026-11-15 | Brak znanych CVE |
| uvicorn | 0.30.6 | BSD-3 | ASGI server | Niskie | 2026-11-15 | |
| anthropic | 0.40.0 | MIT | Silnik OCR (ekstrakcja struktury) | **Wysokie** | 2026-11-15 | Pinowana wersja; zmiana wersji wymaga retestów |
| PyJWT | 2.9.0 | MIT | Uwierzytelnianie JWT | Średnie | 2026-11-15 | Zastąpił python-jose (CVE-2024-33663/33664) |
| bcrypt | 4.2.0 | Apache-2.0 | Haszowanie haseł | Niskie | 2026-11-15 | |
| Pillow | 11.0.0 | HPND | Przetwarzanie obrazów | Niskie | 2026-11-15 | Zaktualizowana z 10.4.0 (CVE-2024-28219) |
| asyncpg | 0.29.0 | Apache-2.0 | Połączenie z PostgreSQL | Niskie | 2026-11-15 | |
| pydantic | 2.8.2 | MIT | Walidacja danych | Niskie | 2026-11-15 | |
| pypdf | 4.3.1 | BSD-3 | Parsowanie PDF | Niskie | 2026-11-15 | |
| pdf2image | 1.17.0 | MIT | Konwersja PDF→obraz | Niskie | 2026-11-15 | Zależy od poppler-utils |
| httpx | 0.27.2 | BSD-3 | Klient HTTP (webhooks) | Niskie | 2026-11-15 | |
| python-dotenv | 1.0.1 | BSD-3 | Zarządzanie konfiguracją | Niskie | 2026-11-15 | |
| redis | 5.0.8 | MIT | Cache / rate limiting | Niskie | 2026-11-15 | |
| nats-py | 2.9.0 | Apache-2.0 | Messaging (przyszłe użycie) | Niskie | 2026-11-15 | |
| python-multipart | 0.0.9 | Apache-2.0 | Upload plików | Niskie | 2026-11-15 | |

## Procedura aktualizacji SOUP

1. `pip-audit -r requirements.txt` — uruchamiany automatycznie w CI na każdy push
2. Przy krytycznym CVE: aktualizacja wersji w `requirements.txt`, update tej tabeli, nowy commit
3. Zmiana wersji `anthropic` wymaga retestów OCR na zestawie 10 dokumentów testowych przed deployem
4. Przegląd rejestru: co 3 miesiące (kwartalny) lub przy każdym wykrytym CVE

## Komponenty zewnętrzne spoza requirements.txt

| Komponent | Wersja | Rola | Uwagi |
|---|---|---|---|
| PostgreSQL (Supabase) | 15.x | Baza danych | Zarządzana przez Supabase |
| nginx | 1.24+ | Reverse proxy, TLS termination | Konfiguracja: `infra/nginx-ikzocr.conf` |
| poppler-utils | system | Konwersja PDF | Instalowany w Dockerfile |
| python:3.11-slim | 3.11 | Base Docker image | Skanowany: Trivy (TODO) |
