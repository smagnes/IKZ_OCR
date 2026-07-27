# IKZOCR — Polityka bezpieczeństwa

> Obowiązuje od: 2026-01-01  
> Właściciel: SZOP sp. z o.o.  
> Przegląd: co 12 miesięcy lub po istotnym incydencie

## 1. Zakres

Niniejsza polityka obejmuje:
- System IKZOCR (SaaS: `panel.ikzocr.pl`, `api.ikzocr.pl`)
- Instalacje On-Premise u klientów (w zakresie dostarczanego oprogramowania)
- Infrastrukturę deweloperską i CI/CD

## 2. Ochrona danych w transmisji

- Cały ruch szyfrowany przez **TLS 1.3** (minimalna wersja: TLS 1.2)
- HTTP przekierowywane do HTTPS (301)
- HSTS włączony (`Strict-Transport-Security: max-age=31536000`)
- Certyfikaty SSL: Let's Encrypt (auto-renewal via certbot)

## 3. Ochrona danych w spoczynku

- Baza danych PostgreSQL: szyfrowanie na poziomie wolumenu (AES-256)
- Hasła użytkowników: **bcrypt** (rounds ≥ 12, nigdy MD5/SHA1)
- Klucze API: przechowywane jako **SHA-256 hash** — plaintext nigdy nie trafia do bazy
- PESEL: maskowany w bazie (`XXXXXX*****`), pełna wartość tylko w session-cache z TTL 1h

## 4. Uwierzytelnianie i autoryzacja

- Klucze API: prefix `mk_` + 24 znaki losowe (CSPRNG)
- JWT tokeny (panel): HS256, TTL 24h, refresh po 23h
- RBAC: role `admin`, `operator`, `readonly`
- MFA wymagane dla kont z rolą `admin`
- Blokada konta po 10 nieudanych próbach logowania (cooldown 15 min)

## 5. Bezpieczeństwo aplikacji

### API
- Rate limiting: 100 req/min per klucz API (Redis sliding window)
- Walidacja plików: tylko obrazy i PDF, max 20 MB, weryfikacja magic bytes
- CORS: tylko zaufane domeny (konfigurowane przez `CORS_ORIGINS`)
- Nagłówki bezpieczeństwa: `X-Content-Type-Options`, `X-Frame-Options`, `CSP`
- Brak logowania treści dokumentów medycznych w logach

### Panel (Next.js)
- CSP blokuje inline scripts i zewnętrzne zasoby
- Cookies sesji: `HttpOnly`, `Secure`, `SameSite=Strict`
- Brak zewnętrznych trackerów / analytics firm trzecich

## 6. Zarządzanie podatnościami

| Obszar | Narzędzie | Częstotliwość |
|--------|-----------|---------------|
| Python deps | `pip audit` / Dependabot | Przy każdym PR |
| Node deps | `npm audit` | Przy każdym PR |
| Docker images | Trivy | Co tydzień |
| OWASP Top 10 | Ręczny checklist | Przed każdym release |
| Pentest zewnętrzny | TBD | Co 12 miesięcy |

Krytyczne podatności (CVSS ≥ 9.0) — patch w ciągu **24h**.  
Wysokie (CVSS 7.0–8.9) — patch w ciągu **7 dni**.

## 7. Dostęp do systemów produkcyjnych

- Dostęp SSH tylko przez klucze (hasła wyłączone)
- `root` login wyłączony; `sudo` z logowaniem
- Firewall (UFW): tylko porty 22, 80, 443
- Dostęp do bazy tylko przez sieć wewnętrzną (nie eksponowany publicznie)
- Dostęp deweloperów do prod: tylko przez bastion host (jeśli Enterprise)

## 8. Backup i odtwarzanie

- Backup PostgreSQL: codziennie o 03:00 UTC, przechowywany 30/60/90 dni (wg planu)
- Backup szyfrowany (GPG) przed uplodem do storage
- Test odtwarzania: co kwartał (RTO: 4h, RPO: 24h)
- Procedura: [`docs/DEPLOYMENT.md#backup`](DEPLOYMENT.md)

## 9. Zgłaszanie podatności (Responsible Disclosure)

Znalazłeś błąd bezpieczeństwa? Skontaktuj się zanim upublicznisz:

**Email:** security@ikzocr.pl  
**PGP:** [klucz publiczny na żądanie]  
**Odpowiedź:** w ciągu 48h  
**Fix:** w ciągu 90 dni dla krytycznych

Prosimy o nieujawnianie szczegółów publicznie przed wdrożeniem patcha.

## 10. Przegląd i audyt

- Przegląd polityki: co 12 miesięcy (lub po incydencie)
- Audyt zewnętrzny: planowany Q4 2026
- Logi dostępu: przechowywane 90 dni, dostęp tylko dla `admin`
- Kontakt w sprawach bezpieczeństwa: security@ikzocr.pl
