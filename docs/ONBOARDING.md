# IKZOCR — Przewodnik onboardingowy

> Ten dokument przeprowadzi Cię przez pierwsze kroki z IKZOCR — od instalacji do pierwszego udanego skanu.

## Dla kogo jest ten przewodnik?

- **Nowy klient SaaS** — masz już dostęp do panelu, chcesz zacząć skanować
- **Administrator IT On-Premise** — instalujesz system na własnym serwerze
- **Deweloper integrujący API** — podłączasz IKZOCR do własnego systemu

---

## Ścieżka A — Klient SaaS (panel.ikzocr.pl)

### Krok 1 — Zaloguj się do panelu

1. Wejdź na https://panel.ikzocr.pl
2. Zaloguj się danymi otrzymanymi w mailu powitalnym
3. Przy pierwszym logowaniu zmień hasło

### Krok 2 — Wygeneruj klucz API

Klucz API potrzebny jest do integracji z Twoim systemem lub do testowania przez curl.

1. W panelu przejdź do **Klucze API** (sidebar → klucz)
2. Kliknij **Nowy klucz**
3. Podaj nazwę (np. `produkcja` lub `test`)
4. **Skopiuj klucz i zapisz go** — wyświetlany jest tylko raz

Klucz wygląda tak: `mk_aBcDeFgHiJkLmNoPqRsTuV`

### Krok 3 — Wykonaj pierwszy skan

**Przez panel:**
1. Sidebar → **Skanuj dokument**
2. Przeciągnij plik lub kliknij "Wybierz plik"
3. Obsługiwane formaty: JPEG, PNG, TIFF, PDF (max 20 MB)
4. Kliknij **Skanuj** — poczekaj 10–45 sekund
5. Wynik pojawi się na ekranie

**Przez API (curl):**
```bash
curl -X POST https://api.ikzocr.pl/v1/scan \
  -H "Authorization: Bearer mk_TwójKlucz" \
  -F "file=@wynik_morfologii.jpg"
```

### Krok 4 — Pobierz wynik w wybranym formacie

Po skanowaniu masz do dyspozycji:
- **JSON** — przez API, pełna struktura danych
- **TXT** — czysty tekst do podglądu
- **MD** — Markdown do dokumentacji
- **CSV** — do importu do Excela lub systemu HIS

W panelu kliknij przyciski **.txt / .md / .csv** przy wyniku.

### Krok 5 — Sprawdź alerty medyczne

Czerwone alerty = wartości krytycznie poza normą (np. ciężka anemia).  
Żółte alerty = wartości wymagające uwagi.  
Alerty służą jako flagi — decyzja kliniczna zawsze należy do lekarza.

### Krok 6 — Skonfiguruj webhook (opcjonalnie)

Jeśli chcesz żeby wyniki trafiały automatycznie do Twojego systemu:

```bash
curl -X POST https://api.ikzocr.pl/v1/webhooks \
  -H "Authorization: Bearer mk_TwójKlucz" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://twoj-system.pl/ikzocr/callback", "events": ["scan.completed"]}'
```

Po każdym skanowaniu IKZOCR wyśle POST z wynikiem na Twój endpoint.

---

## Ścieżka B — Instalacja On-Premise

### Przed instalacją — checklist

```
□ Serwer Linux (Ubuntu 22.04 LTS zalecane)
□ Min. 8 GB RAM, 4 vCPU, 50 GB dysk
□ Docker 24+ i Docker Compose 2.20+
□ Port 80 i 443 otwarty na zewnątrz (lub tylko wewnątrznie)
□ Domena lub IP dla panelu i API
□ Certyfikat SSL (lub Let's Encrypt)
□ Dostęp do internetu przy pierwszym uruchomieniu (pobieranie modeli AI ~1.5 GB)
```

Pełna lista wymagań i instalacja krok po kroku: [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)

### Instalacja w 5 krokach

**1. Pobierz kod**
```bash
git clone https://github.com/smagnes/IKZ_OCR.git /opt/ikzocr
cd /opt/ikzocr
```

**2. Skonfiguruj środowisko**
```bash
cp api/.env.example api/.env
nano api/.env
```

Kluczowe zmienne do ustawienia:
```env
DATABASE_URL=postgresql://medyk:TwojeHaslo@postgres:5432/ikzocr
JWT_SECRET=losowy-string-minimum-32-znaki
CORS_ORIGINS=https://panel.twoja-domena.pl
```

**3. Uruchom**
```bash
docker compose up -d
```

**4. Poczekaj na modele AI**
```bash
docker compose logs -f ocr-api
# Czekaj na: "Models loaded. Ready."
# Pierwsze uruchomienie: 2–5 minut (pobieranie ~1.5 GB)
```

**5. Zweryfikuj**
```bash
curl http://localhost:8000/health
# Oczekiwana odpowiedź: {"status":"ok","version":"0.3.0"}

# Panel
open http://localhost:3000
```

### Pierwsze logowanie (On-Premise)

Po instalacji utwórz konto administratora przez API:

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@twoja-placowka.pl",
    "password": "BezpieczneHaslo123!",
    "org_name": "Nazwa Placówki"
  }'
```

Następnie zaloguj się w panelu pod `http://localhost:3000`.

---

## Ścieżka C — Deweloper / integracja API

### Minimalny przykład w Python

```python
import requests

API_KEY = "mk_TwójKlucz"
API_URL = "https://api.ikzocr.pl"   # lub http://localhost:8000 dla dev

def scan_document(file_path: str) -> dict:
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{API_URL}/v1/scan",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files={"file": f}
        )
    response.raise_for_status()
    return response.json()

# Użycie
result = scan_document("morfologia.jpg")
print(f"Typ: {result['doc_type']}")
print(f"HGB: {result['parsed_data']['labs']['HGB']['value']} g/dL")
print(f"Alerty: {result['alerts']}")
```

### Minimalny przykład w TypeScript / Node.js

```typescript
import FormData from "form-data"
import fetch from "node-fetch"
import fs from "fs"

const API_KEY = "mk_TwójKlucz"
const API_URL = "https://api.ikzocr.pl"

async function scanDocument(filePath: string) {
    const form = new FormData()
    form.append("file", fs.createReadStream(filePath))

    const res = await fetch(`${API_URL}/v1/scan`, {
        method: "POST",
        headers: { Authorization: `Bearer ${API_KEY}`, ...form.getHeaders() },
        body: form
    })

    if (!res.ok) throw new Error(await res.text())
    return res.json()
}

const result = await scanDocument("morfologia.jpg")
console.log(result.parsed_data.labs)
```

### Struktura odpowiedzi JSON

```json
{
  "scan_id": "uuid-...",
  "doc_type": "morphology",
  "confidence": 0.923,
  "processing_time_ms": 12450,
  "parsed_data": {
    "patient": {
      "name": "ANNA KOWALSKA",
      "pesel": "XXXXXX*****",
      "exam_date": "2026-07-15",
      "facility": "Szpital Powiatowy w Iławie"
    },
    "labs": {
      "HGB":  { "value": 12.5, "unit": "g/dL",   "ref_lo": 12.0, "ref_hi": 16.0 },
      "WBC":  { "value":  6.2, "unit": "10³/µL", "ref_lo":  4.5, "ref_hi": 11.0 },
      "PLT":  { "value": 220,  "unit": "10³/µL", "ref_lo": 150,  "ref_hi": 400  }
    }
  },
  "alerts": [
    {
      "param": "HGB",
      "value": 12.5,
      "threshold": 12.0,
      "message": "HGB blisko dolnej granicy normy",
      "level": "info"
    }
  ]
}
```

Pełna referencja API: [`docs/API.md`](API.md)

---

## Co dalej?

| Chcę... | Idź do... |
|---------|-----------|
| Podłączyć IKZOCR do systemu HIS/LIS | [`docs/INTEGRATIONS.md`](INTEGRATIONS.md) |
| Dowiedzieć się jak aktualizować system | [`docs/UPGRADE_GUIDE.md`](UPGRADE_GUIDE.md) |
| Skonfigurować backup danych | [`docs/DEPLOYMENT.md`](DEPLOYMENT.md) |
| Zrozumieć architekturę | [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) |
| Rozbudować lub zmodyfikować kod | [`docs/DEVELOPER.md`](DEVELOPER.md) |
| Sprawdzić cennik i limity | [`docs/PRICING.md`](PRICING.md) |

## Kontakt i wsparcie

- **Email:** support@ikzocr.pl
- **GitHub Issues:** https://github.com/smagnes/IKZ_OCR/issues
- **Dokumentacja:** [`docs/`](.)
