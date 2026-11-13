# IKZOCR v2 dla Dr Kiwi — specyfikacja prac

Wersja 1.0 · 27.10.2026 · autor: Sebastian Magnes (CTO)
Repozytorium: `~/ikzocr_local` (gałąź robocza: `feature/v2-kiwi`)

Dokument jest kompletną listą prac. Każdy punkt ma: co, dlaczego, jak, kryterium odbioru.
Kolejność realizacji jest na końcu (sekcja 15).

---

## 0. Kontekst i decyzje

Keep It Healthy (Dr Kiwi, Jan Kurenda) chce, żeby pacjent wgrywał wyniki badań (PDF/JPG/PNG/HEIC) w aplikacji Kiwi, a IKZOCR zwracał ustrukturyzowany JSON. Kiwi ma gotowy backend: model `ExaminationFile` w `api/models.py`, pliki w prywatnym GCS, endpointy upload dla pacjenta i dietetyka (PDF/JPG/PNG do 10 MB), zdarzenie `OCR_UPLOAD_SUCCESS` i e-mail „wynik wgrany”. Kiwi jest procesorem danych dla placówek, IKZOCR będzie **podprocesorem**.

Stan obecny (sprawdzony w kodzie 27.10.2026), który trzeba zmienić:

| # | Stan dziś | Problem |
|---|-----------|---------|
| 1 | Produkcja API na GCP `us-central1` (IP 34.41.15.71, Iowa, USA) | Dane medyczne poza EOG |
| 2 | `OCR_ENGINE` domyślnie `claude` (`api/ocr/processor.py:13`), wysyłka obrazów do Anthropic API | Transfer do USA, dodatkowy podprocesor |
| 3 | `POST /translate` używa Claude (`main.py:642–708`) | jw. |
| 4 | `scans.raw_text`, `patient`, `doctor`, `pesel_masked` zapisywane w bazie (`db.py:99`) | Przechowujemy PHI, brak retencji |
| 5 | Brak automatycznego usuwania danych w kodzie (DATA_RETENTION.md to deklaruje) | Niezgodność dokumentu z rzeczywistością |
| 6 | `POST /v1/scan/local` nie weryfikuje klucza API (`main.py:744`) | Otwarty endpoint |
| 7 | `/v1/scan/local` zmienia `os.environ["OCR_ENGINE"]` i przeładowuje moduł w trakcie żądania | Wyścig, zmienia silnik dla całego procesu |
| 8 | Paddle inicjalizowany z `lang="en"` (`processor.py:25, 215`) | Gubi polskie znaki (ą, ę, ł, ż) |
| 9 | Domyślny `jwt_secret` w kodzie (`main.py:56`) | Jeśli brak env, tokeny do podrobienia |
| 10 | `seed_demo_keys()` przy każdym starcie (`main.py:101`) | Klucze demo na produkcji |
| 11 | Przetwarzanie synchroniczne, webhook bez podpisu i bez ponowień | Timeouty, brak weryfikacji nadawcy |
| 12 | Brak HEIC, walidacja po `content_type` z nagłówka, nie po zawartości | Zdjęcia z iPhone odrzucane, łatwe obejście |
| 13 | Brak LOINC i ujednolicania jednostek | Kiwi musi mapować sam |
| 14 | Brak sandboxa, OpenAPI publicznie na produkcji | |
| 15 | `ikz_examination_id = abs(hash(scan_id)) % 100000` | Fikcyjne ID, do usunięcia |
| 16 | Grafana z hasłem w README (`admin/medyk2026`) | |

**Decyzje (nie zmieniać bez CTO):**
- D1. Wszystko w UE: GCP `europe-central2` (Warszawa). Żadnych zewnętrznych API AI w ścieżce v2.
- D2. Silnik: wyłącznie lokalny (PaddleOCR + `pdftotext` dla PDF z warstwą tekstową).
- D3. Dwa osobne środowiska: **sandbox** i **produkcja**, osobne projekty GCP, osobne bazy, osobne klucze.
- D4. Domyślnie **zero retencji** dokumentów i treści medycznych.
- D5. Nowe API w przestrzeni `/v2`. `/v1` zostaje tylko na starej instancji do czasu jej wyłączenia.
- D6. Nie używamy danych klientów do trenowania ani ulepszania modeli. Zestawy testowe tylko syntetyczne lub zanonimizowane za zgodą.

---

## 1. Środowiska

### 1.1 Układ

| | Sandbox | Produkcja |
|---|---|---|
| Projekt GCP | `ikzocr-sandbox` | `ikzocr-prod` |
| Region / strefa | `europe-central2` / `-a` | `europe-central2` / `-a` + `-b` |
| Domena API | `sandbox-api.ikzocr.pl` | `eu-api.ikzocr.pl` |
| Prefiks kluczy | `ikz_test_` | `ikz_live_` |
| Dane | tylko syntetyczne (zapis w regulaminie sandboxa) | prawdziwe |
| OpenAPI `/docs` | włączone | wyłączone (`docs_url=None`) |
| Limity | 500 dokumentów/mies., 2 req/s | wg umowy |
| VM | e2-standard-4 | 2 × e2-standard-8 (lub 1 + szybkie odtworzenie, patrz 11) |
| Baza | Cloud SQL PostgreSQL 16, najmniejsza | Cloud SQL PostgreSQL 16, HA, kopie w UE |
| Redis | kontener na VM | Memorystore (Basic) lub kontener na VM |

Ten sam obraz Dockera w obu środowiskach. Różnią się tylko zmienne środowiskowe (`APP_ENV=sandbox|production`).

### 1.2 Infrastruktura jako kod
- Katalog `infra/` z Terraform (VPC, firewall, VM lub MIG, Cloud SQL, Secret Manager, bucket na logi audytu, uptime check, alerty).
- Odbiór: `terraform apply` dla sandboxa stawia całe środowisko od zera w < 30 min.

### 1.3 Sieć i dostęp
- Ruch tylko HTTPS 443 przez HTTP(S) Load Balancer z certyfikatem Google lub Caddy na VM (Let's Encrypt). TLS 1.2+.
- VM bez publicznego IP. SSH wyłącznie przez IAP (`gcloud compute ssh --tunnel-through-iap`).
- Postgres, Redis i Grafana niewystawione na zewnątrz (usunąć `ports:` z compose dla tych usług).
- Firewall: wejście tylko z zakresów LB Google i IAP.
- Opcjonalnie Cloud Armor: limit żądań per IP, blokada krajów spoza listy (do decyzji).

### 1.4 Sekrety
- Wszystkie sekrety w Secret Manager: `DATABASE_URL`, `JWT_SECRET`, `WEBHOOK_SIGNING_MASTER_KEY`, `RESULT_ENCRYPTION_KEY`, SMTP.
- Aplikacja **nie startuje**, jeśli `APP_ENV=production` i któryś sekret ma wartość domyślną lub jest pusty.
- Usunąć `ANTHROPIC_API_KEY` z obrazu v2 i z `.env` v2.

### 1.5 Stara instancja (us-central1)
- Zamrozić: nie podpinać nowych klientów.
- Po migracji: wyeksportować to, co trzeba zachować umownie, usunąć dane osobowe z Supabase (tabela `scans`), wyłączyć VM, udokumentować usunięcie (data, zakres, kto).
- Odbiór: protokół usunięcia w `docs/compliance/`.

---

## 2. Poprawki bezpieczeństwa (P0, przed czymkolwiek innym)

1. **Silnik zablokowany na lokalny.** W v2 usunąć ścieżki Claude i LightOn z obrazu (osobny moduł lub flaga kompilacji obrazu). `OCR_ENGINE` czytany raz przy starcie. Start kończy się błędem, jeśli `APP_ENV=production` i silnik ≠ `paddle`.
2. **Usunąć mutację środowiska w żądaniu** (`os.environ[...]`, `importlib.reload`) z `/v1/scan/local`.
3. **`/v1/scan/local` i `/v1/translate/local`:** w v2 nie istnieją. Na starej instancji dodać `Depends(verify_api_key)` albo wyłączyć.
4. **`/translate` (Claude):** niedostępny w v2.
5. **JWT:** brak wartości domyślnej, minimum 32 bajty losowe, z Secret Manager.
6. **Klucze demo:** `seed_demo_keys()` tylko gdy `APP_ENV=sandbox`.
7. **CORS:** w v2 API jest serwer–serwer, więc CORS wyłączony (brak middleware) poza panelem, który ma własną domenę.
8. **Walidacja plików po zawartości** (magic bytes, `python-magic` lub `filetype`), nie po nagłówku `Content-Type`.
9. **Limit rozmiaru** wymuszony też na proxy (`client_max_body_size 21m`), a nie tylko po wczytaniu do pamięci.
10. **Ochrona przed bombami dekompresji:** `Image.MAX_IMAGE_PIXELS = 80_000_000`, limit stron PDF (sekcja 4), timeout przetwarzania 120 s na dokument.
11. **Hasło Grafany** z sekretu, usunąć z README.
12. **Logi bez danych medycznych:** żadnych fragmentów tekstu, nazwisk, PESEL, nazw plików od klientów. Filtr w `logging` maskujący wzorce PESEL i e-mail jako zabezpieczenie dodatkowe.
13. **Zależności:** `pip-audit` i `npm audit` w CI, obraz skanowany (Artifact Registry vulnerability scanning lub Trivy), SBOM (`syft`) dołączany do wydania.
14. **Fikcyjne `ikz_examination_id`:** usunąć.

Odbiór: test integracyjny, który sprawdza, że w obrazie v2 nie ma pakietu `anthropic` (`pip show anthropic` zwraca błąd) i że żądanie bez klucza do każdego endpointu `/v2` zwraca 401.

---

## 3. Uwierzytelnianie, klucze i limity

- Nagłówek: `Authorization: Bearer ikz_live_xxx` (sandbox: `ikz_test_xxx`). Klucz 32 bajty losowe base62, w bazie tylko SHA-256 + prefiks 8 znaków (jak dziś w `db.py:40`).
- Klucz przypisany do **organizacji** (Keep It Healthy) i środowiska. Klucz testowy nie działa na produkcji i odwrotnie.
- Rotacja: możliwe dwa aktywne klucze naraz, unieważnienie natychmiastowe.
- Limity:
  - miesięczny limit dokumentów wg planu (jak dziś `scans_limit`),
  - limit szybkości per klucz: token bucket w Redis, domyślnie 5 req/s, burst 20 (produkcja), 2 req/s (sandbox),
  - limit równoległych zadań w kolejce per klucz: 50.
- Odpowiedź 429 z nagłówkami `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Opcjonalnie (do decyzji z Kiwi): lista dozwolonych IP backendu Kiwi.

---

## 4. Formaty plików

| Format | MIME | Uwagi |
|---|---|---|
| PDF | `application/pdf` | wielostronicowy, max **20 stron**; PDF z warstwą tekstową idzie przez `pdftotext`, skany przez OCR; PDF zaszyfrowany hasłem: błąd `pdf_encrypted` |
| JPEG | `image/jpeg` | korekta orientacji z EXIF (`ImageOps.exif_transpose`) |
| PNG | `image/png` | |
| WEBP | `image/webp` | |
| TIFF | `image/tiff` | wielostronicowy jak PDF |
| HEIC/HEIF | `image/heic`, `image/heif` | **nowe**: `pillow-heif` (`register_heif_opener()`), korekta orientacji |

- Max rozmiar: **20 MB** na plik (Kiwi ma limit 10 MB, mieści się).
- Obrazy skalowane do dłuższego boku max 3000 px przed OCR (szybkość, pamięć).
- Odbiór: testy jednostkowe dla każdego formatu (próbki w `tests/fixtures/`), w tym HEIC z iPhone obróconego o 90°.

---

## 5. API v2 (asynchroniczne)

### 5.1 Utworzenie zadania
```
POST /v2/jobs
Authorization: Bearer ikz_live_...
Idempotency-Key: <uuid>             # wymagany; ponowienie z tym samym kluczem w 24 h zwraca to samo zadanie
Content-Type: multipart/form-data

file=<plik>
external_id=<id ExaminationFile w Kiwi>     # opcjonalne, wraca w wyniku i webhooku
document_hint=lab|cardiology|discharge|prescription|auto   # opcjonalne, domyślnie auto
callback_url=<https://...>          # opcjonalne, nadpisuje webhook z konfiguracji klucza (musi być na liście dozwolonych domen)
result_ttl=86400                    # sekundy, 3600..604800, domyślnie 86400
```
Odpowiedź `202 Accepted`:
```json
{ "job_id": "job_01J...", "status": "queued", "external_id": "ef_123", "created_at": "2026-11-03T10:00:00Z" }
```

### 5.2 Status i wynik
```
GET /v2/jobs/{job_id}
```
`status`: `queued` → `processing` → `succeeded` | `failed` | `expired`.
Przy `succeeded` odpowiedź zawiera pełny wynik (sekcja 7). Po `result_ttl` wynik jest usunięty, a status to `expired`.

### 5.3 Usunięcie
```
DELETE /v2/jobs/{job_id}     → 204, natychmiast usuwa wynik
```

### 5.4 Tryb synchroniczny (wygoda, małe pliki)
```
POST /v2/scan     # te same pola, odpowiedź 200 z wynikiem albo 202 z job_id, jeśli przetwarzanie > 25 s
```

### 5.5 Webhook
- Zdarzenia: `job.succeeded`, `job.failed`.
- Treść: `{ "event": "job.succeeded", "job_id": "...", "external_id": "...", "created_at": "...", "result_url": "https://eu-api.ikzocr.pl/v2/jobs/job_..." }`.
  Wynik **nie jest** wysyłany w treści webhooka (mniej danych w ruchu, Kiwi pobiera go kluczem). Do decyzji z Kiwi, czy wolą wynik w treści.
- Podpis: nagłówek `IKZOCR-Signature: t=<unix>,v1=<hex HMAC-SHA256(secret, t + "." + body)>`, sekret webhooka per klucz, widoczny raz przy tworzeniu. Odbiorca odrzuca, jeśli |now − t| > 300 s.
- Nagłówki: `IKZOCR-Event`, `IKZOCR-Delivery-Id` (do deduplikacji).
- Ponowienia: przy kodzie ≠ 2xx lub timeout 10 s: po 30 s, 2 min, 10 min, 1 h, 6 h (5 prób), potem `delivery_failed` w logu i alert.
- Tylko `https://`, blokada adresów prywatnych i metadanych (ochrona SSRF: odrzucić 10/8, 172.16/12, 192.168/16, 127/8, 169.254/16, `::1`).
- Endpoint testowy w sandboxie: `POST /v2/webhooks/test` wysyła przykładowe zdarzenie.

### 5.6 Kody błędów (jednolite)
```json
{ "error": { "code": "unsupported_format", "message": "...", "request_id": "req_..." } }
```
Kody: `unauthorized` 401, `forbidden` 403, `not_found` 404, `file_too_large` 413, `unsupported_format` 415, `pdf_encrypted` 422, `too_many_pages` 422, `image_quality_too_low` 422 (z `reasons[]`), `rate_limited` 429, `quota_exceeded` 429, `processing_timeout` 504, `internal_error` 500.
Każda odpowiedź ma nagłówek `X-Request-Id`.

### 5.7 Kolejka i workery
- Kolejka: Redis + RQ (prosto) albo Celery. Plik w kolejce trzymany **tylko w Redis, zaszyfrowany** (AES-GCM, `RESULT_ENCRYPTION_KEY`), z TTL 1 h. Nie zapisujemy go na dysk ani do bucketu.
- Workery: osobny proces lub kontener `ocr-worker`, liczba = liczba vCPU / 2. Modele Paddle ładowane raz na worker.
- API (`uvicorn`) nie wykonuje OCR, tylko przyjmuje i oddaje.

---

## 6. Retencja i prywatność (zero retencji)

Dla v2 domyślnie:

| Dane | Gdzie | Jak długo |
|---|---|---|
| Plik źródłowy | Redis, zaszyfrowany, tylko w czasie kolejki | do końca przetwarzania, max 1 h |
| Wynik (JSON) | Redis, zaszyfrowany | `result_ttl` (domyślnie 24 h) lub do `DELETE` |
| Metadane zadania | Postgres `jobs` | 90 dni (rozliczenia, audyt) |
| Logi techniczne | Cloud Logging, bucket w `europe-central2` | 90 dni |
| Kopie bazy | Cloud SQL backup w UE | 30 dni (nie zawierają danych medycznych) |

- Tabela `jobs` zawiera **tylko**: `id, api_key_id, external_id, status, doc_type, pages, file_size, mime, duration_ms, error_code, created_at, finished_at, webhook_status`. **Bez** nazwiska, PESEL, tekstu, wartości wyników, nazwy pliku.
- Pliki tymczasowe przy konwersji PDF/HEIC: wyłącznie w `tmpfs` (`/dev/shm` lub wolumen `tmpfs` w compose), usuwane w `finally`.
- Dane identyfikujące pacjenta w wyniku: domyślnie **nie zwracamy** imienia, nazwiska ani PESEL (`return_identity=false`). Kiwi zna pacjenta. Opcjonalnie zwracamy `identity_check`: `{ "name_present": true, "pesel_present": true }` bez wartości, żeby Kiwi mógł ostrzec, że dokument może należeć do innej osoby (opcja do włączenia per klucz).
- Zadanie cykliczne (`cron` co godzinę): usuwa metadane starsze niż 90 dni, weryfikuje brak osieroconych kluczy w Redis.
- Odbiór: test, który po zakończeniu zadania i upływie TTL sprawdza brak jakichkolwiek danych zadania w Redis i brak treści medycznych w Postgres (zapytanie po wszystkich kolumnach tekstowych).

Zaktualizować `docs/legal/DATA_RETENTION.md` dokładnie do tej tabeli.

---

## 7. Format wyniku (JSON v2)

> Do dopasowania: Jan przesłał oczekiwany kształt JSON (link 1Password). Wkleić go tutaj i uzgodnić nazwy pól przed implementacją. Poniżej propozycja bazowa.

```json
{
  "job_id": "job_01J...",
  "external_id": "ef_123",
  "status": "succeeded",
  "schema_version": "2.0",
  "engine": { "name": "ikzocr-local", "version": "2.0.0" },
  "document": {
    "type": "lab_result",                // lab_result | cardiology | discharge_summary | prescription | referral | other
    "subtype": "lipid_panel",            // cbc | lipid_panel | glucose | thyroid | urinalysis | ecg | echo | holter | ...
    "laboratory": "ALAB laboratoria",    // nazwa podmiotu z dokumentu, jeśli odczytana
    "collected_at": "2026-10-21",        // data pobrania
    "reported_at": "2026-10-22",
    "pages": 1,
    "language": "pl"
  },
  "results": [
    {
      "name_raw": "Cholesterol LDL",
      "name": "LDL cholesterol",
      "loinc": "13457-7",
      "value_raw": "162",
      "value": 162.0,
      "value_type": "numeric",           // numeric | qualitative | text
      "unit_raw": "mg/dl",
      "unit": "mg/dL",                   // UCUM
      "value_si": 4.19,
      "unit_si": "mmol/L",
      "reference": { "low": null, "high": 115.0, "text": "< 115" },
      "flag": "H",                       // L | N | H | A (nieprawidłowy, jakościowy) | null
      "confidence": 0.97,
      "page": 1
    },
    {
      "name_raw": "Białko",
      "name": "Protein [Presence] in Urine",
      "loinc": "20454-5",
      "value_raw": "nieobecne",
      "value_type": "qualitative",
      "value": "negative",
      "flag": "N",
      "confidence": 0.93,
      "page": 1
    }
  ],
  "narrative": [
    { "section": "Wnioski", "text": "Rytm zatokowy miarowy 72/min..." }
  ],
  "quality": {
    "overall": 0.95,
    "needs_review": false,
    "reasons": []                        // blur | low_resolution | glare | cropped | handwriting | unknown_layout | low_confidence_values
  },
  "warnings": [],
  "processing_ms": 4210
}
```

Zasady:
- **Nie zgadujemy.** Jeśli wartość lub jednostka nieczytelna: pole pomijamy albo `value: null` + `confidence` < próg + `quality.needs_review = true`.
- Próg `needs_review`: dowolny wynik z `confidence < 0.85` lub brak jednostki przy wartości liczbowej.
- `flag` liczymy z zakresu referencyjnego **z dokumentu**, nie z własnych norm. Jeśli dokument ma własną flagę (H/L, *, ↑), ma pierwszeństwo.
- `raw_text` **nie** jest zwracany domyślnie (opcja `include_text=true` per klucz, do decyzji).
- JSON Schema w `api/schemas/result_v2.schema.json`, walidowany w testach.

---

## 8. Normalizacja: LOINC i jednostki

### 8.1 Słownik
- Plik `api/ocr/dictionary/lab_pl.yaml`: dla każdego parametru: warianty nazw polskich (z laboratoriów ALAB, Diagnostyka, Synevo, LUX MED, Medicover, szpitale), LOINC, jednostka UCUM, przeliczniki.
- Start: ok. 60 najczęstszych parametrów. Minimum na odbiór:

| Parametr | LOINC (do weryfikacji na loinc.org) | Jednostka | Przelicznik SI |
|---|---|---|---|
| WBC | 6690-2 | 10*3/uL | |
| RBC | 789-8 | 10*6/uL | |
| Hemoglobina | 718-7 | g/dL | ×0,6206 → mmol/L |
| Hematokryt | 4544-3 | % | |
| MCV / MCH / MCHC | 787-2 / 785-6 / 786-4 | fL / pg / g/dL | |
| PLT | 777-3 | 10*3/uL | |
| RDW-CV | 788-0 | % | |
| Neutrofile / limfocyty (bezwzgl.) | 751-8 / 731-0 | 10*3/uL | |
| Cholesterol całkowity | 2093-3 | mg/dL | ×0,02586 → mmol/L |
| HDL | 2085-9 | mg/dL | ×0,02586 |
| LDL (wyliczony / bezpośredni) | 13457-7 / 18262-6 | mg/dL | ×0,02586 |
| Trójglicerydy | 2571-8 | mg/dL | ×0,01129 |
| Glukoza (surowica / na czczo) | 2345-7 / 1558-6 | mg/dL | ×0,0555 |
| HbA1c | 4548-4 | % | |
| TSH | 3016-3 | m[IU]/L | |
| FT4 / FT3 | 3024-7 / 3051-0 | ng/dL / pg/mL | |
| Kreatynina | 2160-0 | mg/dL | ×88,4 → µmol/L |
| eGFR | 62238-1 (lub nowszy kod CKD-EPI 2021) | mL/min/{1.73_m2} | |
| ALT / AST | 1742-6 / 1920-8 | U/L | |
| GGTP | 2324-2 | U/L | |
| CRP | 1988-5 | mg/L | |
| Kwas moczowy | 3084-1 | mg/dL | |
| Badanie ogólne moczu (białko, glukoza, ciała ketonowe, krew) | 20454-5, 25428-4, 2514-8, 20409-9 | jakościowe | |

Kody LOINC sprawdzić w oficjalnej bazie przed wydaniem. Tabela jest punktem startowym.

### 8.2 Zasady
- Zawsze zwracamy wartość i jednostkę **oryginalną** (`value_raw`, `unit_raw`) obok znormalizowanej.
- Gdy nie ma mapowania: `loinc: null`, `name = name_raw`, wynik i tak wraca.
- Przecinek dziesiętny → kropka. „<0,01”, „>200” → `value` liczbowe + `value_raw` bez zmian + `comparator: "<"`.
- Odbiór: testy jednostkowe przeliczeń i mapowań dla każdego wiersza tabeli.

---

## 9. Jakość odczytu i trudne przypadki

### 9.1 Silnik
- Paddle: `lang="pl"` (model łaciński z polskimi znakami) zamiast `"en"`. Zweryfikować na zestawie testowym, że „ą ę ł ś ż” są odczytywane.
- Zachować istniejący preprocessing (`_preprocess`, `_deskew`) i dodać: korekta EXIF, wykrycie i przycięcie kartki na zdjęciu (kontur, transformacja perspektywy w OpenCV).

### 9.2 Ocena jakości przed OCR
- Ostrość: wariancja Laplasjanu. Rozdzielczość: krótszy bok < 800 px → `low_resolution`. Prześwietlenia: odsetek pikseli nasyconych.
- Bardzo zła jakość (np. ostrość poniżej progu i średnia pewność OCR < 0,5): zadanie kończy się `failed` z `image_quality_too_low` i `reasons[]`, żeby Kiwi poprosił pacjenta o ponowne zdjęcie. Progi skalibrować na zestawie testowym.

### 9.3 Wyniki opisowe
- Badanie moczu, posiew, cytologia: wartości jakościowe (`value_type: qualitative`) ze słownikiem („nieobecne” → `negative`, „ślad” → `trace`, „+”/„++” → `1+`/`2+`).
- Treść opisowa trafia do `narrative[]` z nagłówkiem sekcji, bez interpretacji.

### 9.4 Kardiologia
- Klasyfikacja: `ecg`, `echo`, `holter_ecg`, `holter_bp` (ABPM), `stress_test`, `cardiology_consult`.
- Z opisów wyciągamy **tylko jawnie zapisane** liczby: HR, PQ, QRS, QTc, EF (%), wymiary jam serca, średnie ciśnienia z ABPM. Reszta jako `narrative`.
- Nie analizujemy samego zapisu EKG (krzywej). To wyrób medyczny, poza zakresem.

### 9.5 Zdjęcia wyświetlaczy (ciśnieniomierz, glukometr)
- **Poza zakresem v2.** Osobny moduł w fazie 2: model do wyświetlaczy siedmiosegmentowych, osobny zestaw testowy na zdjęciach seniorów, osobna wycena. W v2 takie zdjęcie zwraca `document.type = "other"` i `needs_review = true`.

### 9.6 Zestaw testowy i jakość
- `tests/golden/`: min. 40 dokumentów: ALAB, Diagnostyka, Synevo, LUX MED, Invicta, szpital powiatowy (próbki z `~/Desktop/OCR TEST`, wyłącznie zanonimizowane lub syntetyczne), po kilka zdjęć z telefonu (krzywo, w złym świetle, HEIC), 3 PDF wielostronicowe, 3 kardiologia, 3 badanie moczu.
- Do każdego ręcznie przygotowany oczekiwany JSON.
- Skrypt `scripts/eval.py`: dokładność na poziomie pól (nazwa + wartość + jednostka), odsetek `needs_review`, czas p50/p95.
- CI: spadek dokładności o > 2 pkt proc. względem ostatniego wydania blokuje merge.
- Odbiór: raport `docs/EVAL_v2.md` z wynikami. **Te liczby podajemy Kiwi, nie wcześniej.**

---

## 10. Wydajność

- Cel do weryfikacji testem: p95 < 15 s dla 1 strony zdjęcia, < 5 s dla PDF z warstwą tekstową, na e2-standard-8.
- Test obciążeniowy (`locust` lub `k6`): 200 dokumentów w 10 min, bez błędów 5xx, kolejka się opróżnia.
- Metryki Prometheus: długość kolejki, czas zadania, odsetek błędów, odsetek `needs_review`. Alerty: kolejka > 100 przez 10 min, błędy 5xx > 2%, health check down > 2 min.

---

## 11. Ciągłość działania i kopie

- RPO 1 h, RTO 4 h (spójnie z polityką NIS2 IKZ).
- Cloud SQL: automatyczne kopie dzienne + PITR, w UE.
- Obraz Dockera w Artifact Registry `europe-central2`, wersjonowany tagami (`v2.0.0`), wdrożenie przez skrypt lub CI, rollback do poprzedniego tagu jedną komendą.
- Test odtworzenia sandboxa od zera z Terraform + kopii bazy raz na kwartał, protokół w `docs/compliance/`.
- Strona statusu (np. prosty uptime check + publiczna strona) do decyzji.

---

## 12. Dokumentacja dla integratora

- `docs/api/v2.md`: uwierzytelnianie, endpointy, kody błędów, webhook z przykładem weryfikacji podpisu w Pythonie (Django, bo Kiwi ma `api/models.py`) i Node.
- OpenAPI 3.1 generowany z FastAPI, publikowany na sandboxie (`/docs`) i jako plik `docs/api/openapi-v2.json`.
- Kolekcja Postman v2 ze zmiennymi środowisk sandbox/produkcja.
- 4 przykładowe odpowiedzi JSON z dokumentów syntetycznych: morfologia, lipidogram, glukoza, TSH (`docs/api/examples/`). Dodatkowo: badanie moczu i opis echa serca.
- Przewodnik integracji dla Kiwi (sekcja 13) jako osobny plik `docs/api/kiwi-integration.md`.

---

## 13. Ścieżka end-to-end z Kiwi

1. Pacjent lub dietetyk wgrywa plik w Kiwi. Kiwi zapisuje `ExaminationFile` w prywatnym GCS (bez zmian).
2. Backend Kiwi (zadanie w tle, serwer–serwer) wysyła plik do `POST /v2/jobs` z `external_id = ExaminationFile.id` i `Idempotency-Key = ExaminationFile.id`.
3. IKZOCR przetwarza, wysyła webhook `job.succeeded` na endpoint Kiwi.
4. Kiwi weryfikuje podpis, pobiera wynik `GET /v2/jobs/{id}`, zapisuje wartości przy badaniu, wywołuje `OCR_UPLOAD_SUCCESS` i e-mail „wynik wgrany”.
5. Kiwi wywołuje `DELETE /v2/jobs/{id}` (albo wynik wygasa sam po TTL).
6. Gdy `needs_review = true` albo `failed: image_quality_too_low`: Kiwi pokazuje dietetykowi wynik do sprawdzenia albo prosi pacjenta o lepsze zdjęcie.

Przeglądarka pacjenta nigdy nie łączy się z IKZOCR.

---

## 14. Dokumenty zgodności (NIS2, RODO) dla IKZOCR

Bazujemy na pakiecie IKZ (`~/Desktop/Procderury IKZ/`, Konkludi Med, wersja 30.05.2026). Dla IKZOCR trzeba zrobić kopie i dostosować: nazwę podmiotu, zakres usługi (OCR jako podprocesor), dostawców, RTO/RPO, retencję.

> **Decyzja przed startem:** który podmiot jest dostawcą IKZOCR (Konkludi Med? SZOP sp. z o.o., jak w obecnym `DATA_RETENTION.md`? nowa spółka?). Od tego zależą wszystkie umowy.

| Dokument | Źródło w pakiecie IKZ | Co zmienić dla IKZOCR |
|---|---|---|
| Polityka zgodności NIS2 | `NIS2 IKZ.pages` | Zakres: usługa OCR; mapa art. 21 na środki z tej specyfikacji; rejestr ryzyk (sekcja 16); łańcuch dostaw: tylko Google Cloud (EU) |
| Polityka Bezpieczeństwa Informacji | `Polityka Bezpieczenstwa Informacji IKZ.pages` | Sekcje sieć, sekrety, logi, kopie wg sekcji 1–2, 11 |
| Procedura obsługi incydentów | `Procedura Obslugi Incydentow IKZ.pages` | Dodać: powiadomienie administratora/procesora (Kiwi) bez zbędnej zwłoki, cel ≤ 24 h, żeby zdążył z 72 h dla UODO; NIS2 24 h / 72 h / 1 mies. |
| Umowa powierzenia (DPA) | `Umowa Powierzenia Danych DPA IKZ.pages` | Wersja **podpowierzenia** (Kiwi → IKZOCR): cel wyłącznie OCR, zakaz trenowania modeli, zero retencji, lokalizacja EOG, prawo audytu, lista podprocesorów, usunięcie danych po zakończeniu umowy |
| Rejestr kategorii czynności | `Rejestr Czynności IKZ.pages` | Wersja procesora (art. 30 ust. 2 RODO) |
| SLA | `Polityka SLA IKZ.pages` | Dostępność, czasy reakcji, okna serwisowe dla API v2 |
| Polityka retencji | `docs/legal/DATA_RETENTION.md` | Dokładnie tabela z sekcji 6 |
| Opis środków technicznych i organizacyjnych (TOMs) | brak, **nowy** | 2–3 strony: szyfrowanie, dostęp, logi, kopie, lokalizacja, testy, szkolenia |
| Lista podprocesorów | brak, **nowy** | Google Cloud EMEA Ltd., region europe-central2; ewentualnie dostawca SMTP (jeśli używany w v2, inaczej usunąć) |
| Odpowiedzi na typową ankietę bezpieczeństwa | brak, **nowy** | Na bazie pytań Jana z 27.10.2026 |
| Wsparcie DPIA dla klienta | brak, **nowy** | 1 strona: opis przetwarzania, ryzyka, środki |

ISO 27001: **brak certyfikatu**. Tak to komunikujemy. Google Cloud ma ISO 27001/27017/27018 i SOC 2 dla infrastruktury. Środki IKZOCR mapujemy na Annex A w polityce NIS2 (jak w IKZ).

Dodatkowo przed produkcją: skan podatności (OWASP ZAP na sandboxie) i raport w `docs/compliance/`. Zewnętrzny pentest zalecany przed pierwszą placówką na dużą skalę.

---

## 15. Kolejność i szacunek

| Etap | Zakres | Szacunek |
|---|---|---|
| 1 | Sekcja 2 (poprawki bezpieczeństwa) + `lang="pl"` | 1 dzień |
| 2 | Sekcja 1 (sandbox w Warszawie, Terraform, sekrety, IAP) | 1–2 dni |
| 3 | Sekcje 4–6 (HEIC, kolejka, `/v2/jobs`, webhook z podpisem, zero retencji) | 2–3 dni |
| 4 | Sekcja 7–8 (JSON v2, słownik LOINC 60 parametrów, przeliczniki) | 2 dni |
| 5 | Sekcja 9 (ocena jakości, opisowe, kardiologia, zestaw testowy, eval) | 2–3 dni |
| 6 | Sekcje 10–12 (testy obciążeniowe, monitoring, dokumentacja, przykłady JSON) | 1–2 dni |
| 7 | Produkcja w Warszawie + wygaszenie us-central1 | 1 dzień |
| 8 | Sekcja 14 (dokumenty, adaptacja pakietu IKZ) | 2 dni, równolegle |

Razem ok. **10–14 dni roboczych** jednej osoby. Sandbox dla Kiwi (etapy 1–3 + przykładowe JSON-y) realnie po ok. 5 dniach.

---

## 16. Rejestr ryzyk (do polityki NIS2)

| Ryzyko | Prawdop. | Wpływ | Środek |
|---|---|---|---|
| Wyciek dokumentów medycznych | niskie | wysoki | zero retencji, szyfrowanie w kolejce, brak publicznego IP, IAP |
| Błędny odczyt wartości prowadzący do złej decyzji | średnie | wysoki | `confidence`, `needs_review`, oryginalna wartość obok, brak zgadywania, eval w CI |
| Niedostępność usługi | średnie | średni | kolejka, ponowienia webhooka, RTO 4 h, monitoring |
| Przejęcie klucza API | niskie | wysoki | hash, rotacja, limit szybkości, opcjonalnie lista IP |
| Podatność w zależnościach | średnie | średni | `pip-audit`, skan obrazu, SBOM, aktualizacje co miesiąc |
| Uznanie OCR za wyrób medyczny (MDR) | niskie | wysoki | brak interpretacji klinicznej, brak analizy krzywych EKG, flagi tylko z zakresów z dokumentu |

---

## 17. Kryteria odbioru (checklista)

- [ ] W obrazie v2 brak pakietu `anthropic` i brak wywołań zewnętrznych API AI
- [ ] Sandbox i produkcja działają w `europe-central2`, osobne projekty, osobne klucze
- [ ] VM bez publicznego IP, SSH tylko przez IAP, sekrety w Secret Manager
- [ ] `/v2/jobs`, `/v2/jobs/{id}`, `DELETE`, `/v2/scan` działają, testy przechodzą
- [ ] Webhook z podpisem HMAC, ponowienia, ochrona SSRF, endpoint testowy w sandboxie
- [ ] PDF wielostronicowy, JPG, PNG, WEBP, TIFF, HEIC (z korektą orientacji)
- [ ] Brak danych medycznych w Postgres i logach (test automatyczny)
- [ ] Wynik usuwany po TTL i po `DELETE` (test automatyczny)
- [ ] JSON zgodny z `result_v2.schema.json` i z formatem uzgodnionym z Kiwi
- [ ] LOINC + UCUM dla min. 60 parametrów, przeliczniki z testami
- [ ] Polskie znaki poprawnie odczytywane (`lang="pl"`)
- [ ] Raport `EVAL_v2.md` na min. 40 dokumentach
- [ ] Test obciążeniowy zaliczony, alerty skonfigurowane
- [ ] Dokumentacja API, OpenAPI, Postman, 4+ przykładowe JSON-y
- [ ] Dokumenty z sekcji 14 gotowe do podpisu
- [ ] Stara instancja us-central1 wyłączona, dane usunięte, protokół zapisany
