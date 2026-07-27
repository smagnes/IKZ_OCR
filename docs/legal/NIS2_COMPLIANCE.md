# IKZOCR — Zgodność z dyrektywą NIS2

> Dyrektywa NIS2 (UE 2022/2555) — Network and Information Security  
> Implementacja w Polsce: Ustawa o krajowym systemie cyberbezpieczeństwa (KSC)  
> Dokument przeglądany: co 12 miesięcy lub po istotnej zmianie systemu

## Zakres stosowania

IKZOCR jako system przetwarzający dane medyczne może stanowić element infrastruktury podmiotów z sektora **ochrony zdrowia** — jednego z sektorów kluczowych wymienionych w NIS2 (Załącznik I).

**Dostawca systemu (SZOP sp. z o.o.)** pełni rolę **dostawcy usług cyfrowych** dla podmiotów ochrony zdrowia i wdraża środki NIS2 odpowiednie dla tej roli.

---

## Środki zarządzania ryzykiem (art. 21 NIS2)

### 1. Polityki bezpieczeństwa systemów informatycznych

- [x] Polityka bezpieczeństwa informacji (aktualizowana rocznie)
- [x] Polityka zarządzania dostępem (RBAC, zasada najmniejszych uprawnień)
- [x] Polityka haseł i uwierzytelniania
- [x] Polityka aktualizacji oprogramowania (Watchtower / harmonogram patches)

### 2. Obsługa incydentów

| Etap | Działanie | Czas |
|------|-----------|------|
| Wykrycie | Monitoring automatyczny (Prometheus/Grafana) + logi | Ciągłe |
| Klasyfikacja | Ocena istotności przez zespół | < 1h |
| Zgłoszenie (istotne) | Powiadomienie klienta + CERT Polska | < 24h |
| Zgłoszenie (poważne) | Powiadomienie organu nadzorczego | < 72h |
| Raport końcowy | Po zakończeniu incydentu | < 30 dni |

**Kontakt incydentowy:** security@ikzocr.pl  
**CERT Polska:** https://incydent.cert.pl

### 3. Ciągłość działania

- [x] Automatyczne kopie zapasowe bazy danych (codziennie, szyfrowane)
- [x] Procedura przywracania (RTO: 4h, RPO: 24h)
- [x] Środowisko DR (disaster recovery) — opcja Enterprise
- [x] Monitoring dostępności (health check co 60 sekund)
- [x] Automatyczny restart kontenerów (`restart: unless-stopped`)

### 4. Bezpieczeństwo łańcucha dostaw

Komponenty zewnętrzne używane w IKZOCR:

| Komponent | Dostawca | Weryfikacja |
|-----------|----------|-------------|
| Surya OCR | VikParuchuri (open source) | Przegląd kodu, pinned version |
| FastAPI | Sebastián Ramírez (open source) | PyPI, pinned version |
| PostgreSQL | PostgreSQL Global Development Group | Oficjalny obraz Docker |
| Next.js | Vercel (open source) | npm audit, pinned version |
| Docker | Docker Inc. | Oficjalne repozytorium |

### 5. Bezpieczeństwo przy nabywaniu, rozwijaniu i utrzymywaniu systemów

- [x] Code review przed każdym wdrożeniem produkcyjnym
- [x] Testy bezpieczeństwa (OWASP Top 10 checklist)
- [x] Zarządzanie podatnościami (Dependabot / ręczny przegląd)
- [x] Separacja środowisk (dev / staging / production)

### 6. Szkolenia z cyberbezpieczeństwa

- [x] Szkolenie onboardingowe dla nowych pracowników
- [x] Roczne przypomnienie procedur bezpieczeństwa
- [x] Procedura reagowania na phishing

### 7. Kryptografia

- Dane w spoczynku: **AES-256**
- Dane w transmisji: **TLS 1.3** (minimalna wersja TLS 1.2)
- Hasła: **bcrypt** (rounds ≥ 12)
- Tokeny JWT: **HS256** / **RS256**, TTL: 24h
- Klucze API: **SHA-256** hash w bazie (nigdy plaintext)

### 8. Kontrola dostępu i zarządzanie tożsamością

- [x] Uwierzytelnianie wieloskładnikowe (MFA) dla adminów
- [x] RBAC (role: admin, operator, readonly)
- [x] Automatyczne wygaszanie sesji (24h JWT)
- [x] Logi dostępu z IP, timestampem, akcją

### 9. Bezpieczeństwo fizyczne

*Dotyczy On-Premise — odpowiedzialność klienta.*  
*Dotyczy SaaS — odpowiedzialność centrum danych (ISO 27001).*

### 10. Zarządzanie aktywami

- [x] Rejestr komponentów (SBOM — Software Bill of Materials dostępny na żądanie)
- [x] Inwentaryzacja danych (kategorie, lokalizacja, właściciel)

---

## Raportowanie incydentów

Zgodnie z art. 23 NIS2, poważne incydenty cyberbezpieczeństwa są zgłaszane do:

1. **Klienta** (dotkniętej placówki) — w ciągu 24 godzin
2. **CERT Polska** — https://incydent.cert.pl — w ciągu 72 godzin
3. **UKNF** (jeśli dotyczy podmiotów finansowych) — zgodnie z odrębnymi wymogami

**Definicja poważnego incydentu** (NIS2 art. 23 ust. 3):
- Zakłócenie usługi > 4h lub
- Naruszenie danych > 500 osób lub
- Strata finansowa > 500 000 EUR

---

## Ocena zgodności

| Obszar | Status | Uwagi |
|--------|--------|-------|
| Polityki bezpieczeństwa | ✅ Wdrożone | Przegląd co 12 mies. |
| Obsługa incydentów | ✅ Wdrożone | Procedura w security@ikzocr.pl |
| Backup i ciągłość | ✅ Wdrożone | RPO 24h, RTO 4h |
| Kryptografia | ✅ Wdrożone | AES-256, TLS 1.3 |
| Kontrola dostępu | ✅ Wdrożone | RBAC + MFA |
| Łańcuch dostaw | ✅ Monitorowane | Przegląd kwartalny |
| Szkolenia | 🔄 W trakcie | Program Q3 2026 |
| Audyt zewnętrzny | ⏳ Planowany | Q4 2026 |

---

Kontakt w sprawach NIS2/bezpieczeństwa: security@ikzocr.pl
