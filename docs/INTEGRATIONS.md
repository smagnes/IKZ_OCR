# IKZOCR — Integracje z systemami zewnętrznymi

## Spis treści

1. [REST API — podstawy integracji](#1-rest-api--podstawy-integracji)
2. [Webhook — wyniki w czasie rzeczywistym](#2-webhook--wyniki-w-czasie-rzeczywistym)
3. [Integracja z systemem HIS/LIS](#3-integracja-z-systemem-hislis)
4. [Eksport do CSV i import do Excela / bazy danych](#4-eksport-do-csv-i-import-do-excela--bazy-danych)
5. [Przykłady kodu](#5-przykłady-kodu)
6. [Integracja z aplikacją mobilną Flutter](#6-integracja-z-aplikacją-mobilną-flutter)
7. [Roadmap integracji](#7-roadmap-integracji)

---

## 1. REST API — podstawy integracji

Każda integracja z IKZOCR opiera się na kluczu API (Bearer token) i endpoincie `POST /v1/scan`.

### Schemat przepływu

```
Twój system                     IKZOCR API
     │                               │
     │── POST /v1/scan ─────────────►│
     │   file=<obraz/PDF>            │── OCR (10–45s)
     │   Authorization: Bearer mk_xx │── parse
     │                               │── save
     │◄── JSON wynik ───────────────│
     │   {scan_id, doc_type,         │
     │    parsed_data, alerts}        │
     │                               │
     │── GET /v1/documents ─────────►│  (historia, polling)
     │◄── lista skanów ─────────────│
```

### Uwierzytelnianie

```http
Authorization: Bearer mk_TwójKluczAPI
```

Klucz generowany w panelu: **Panel → Klucze API → Nowy klucz**

### Limity

| Plan | Skanów/miesiąc | Rozmiar pliku | Timeout |
|------|----------------|--------------|---------|
| Starter | 200 | 20 MB | 120s |
| Pro | 1 000 | 20 MB | 120s |
| Enterprise | 5 000+ | 20 MB | 120s |

---

## 2. Webhook — wyniki w czasie rzeczywistym

Zamiast pollować API, zarejestruj endpoint webhook — IKZOCR wyśle wynik zaraz po zakończeniu skanowania.

### Rejestracja webhooka

```bash
curl -X POST https://api.ikzocr.pl/v1/webhooks \
  -H "Authorization: Bearer mk_TwójKlucz" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://twoj-system.pl/api/ikzocr/callback",
    "events": ["scan.completed", "scan.failed"],
    "secret": "twój-sekret-do-weryfikacji-podpisu"
  }'
```

### Payload webhooka (scan.completed)

```json
{
  "event": "scan.completed",
  "timestamp": "2026-07-27T14:32:00Z",
  "scan_id": "uuid-...",
  "doc_type": "morphology",
  "confidence": 0.923,
  "parsed_data": {
    "patient": { "name": "ANNA KOWALSKA", "pesel": "XXXXXX*****" },
    "labs": {
      "HGB": { "value": 12.5, "unit": "g/dL", "ref_lo": 12.0, "ref_hi": 16.0 }
    }
  },
  "alerts": [
    { "param": "HGB", "level": "warning", "message": "HGB poniżej normy" }
  ]
}
```

### Weryfikacja podpisu webhooka

IKZOCR podpisuje każdy webhook nagłówkiem `X-IKZOCR-Signature: sha256=<hmac>`.

```python
# Python — weryfikacja podpisu
import hmac, hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

# W handlerze:
@app.post("/api/ikzocr/callback")
async def ikzocr_callback(request: Request):
    payload = await request.body()
    sig = request.headers.get("X-IKZOCR-Signature", "")
    if not verify_webhook(payload, sig, WEBHOOK_SECRET):
        raise HTTPException(401, "Invalid signature")
    
    data = await request.json()
    # Przetwórz dane...
    return {"status": "ok"}
```

---

## 3. Integracja z systemem HIS/LIS

### Schemat integracji asynchronicznej (zalecane)

```
┌─────────────────┐     ①skan     ┌──────────────┐
│   Twój HIS/LIS  │──────────────►│  IKZOCR API  │
│                 │               │              │
│  ②webhook      │◄──────────────│  ③wynik JSON  │
│                 │  scan.complete │              │
└────────┬────────┘               └──────────────┘
         │
         ④ import do bazy HIS
         │
         ▼
┌─────────────────┐
│  Wyniki w HIS   │
│  (gotowe do     │
│   przeglądu)    │
└─────────────────┘
```

### Mapowanie pól JSON → pola HIS

Przykład mapowania dla typowego HIS obsługującego HL7 v2:

```python
def ikzocr_to_hl7_obx(scan_result: dict) -> list[dict]:
    """Mapuje wyniki IKZOCR na segmenty OBX (HL7 v2.x)."""
    labs = scan_result["parsed_data"].get("labs", {})
    obx_segments = []

    PARAM_MAP = {
        "HGB":  {"loinc": "718-7",  "name": "Hemoglobin [Mass/volume] in Blood"},
        "WBC":  {"loinc": "6690-2", "name": "Leukocytes [#/volume] in Blood"},
        "RBC":  {"loinc": "789-8",  "name": "Erythrocytes [#/volume] in Blood"},
        "PLT":  {"loinc": "777-3",  "name": "Platelets [#/volume] in Blood"},
        "HCT":  {"loinc": "4544-3", "name": "Hematocrit [Volume Fraction] of Blood"},
    }

    for i, (param, data) in enumerate(labs.items(), start=1):
        if param not in PARAM_MAP:
            continue
        obx_segments.append({
            "set_id": i,
            "value_type": "NM",
            "observation_id": PARAM_MAP[param]["loinc"],
            "observation_name": PARAM_MAP[param]["name"],
            "value": data["value"],
            "unit": data.get("unit", ""),
            "reference_range": f"{data['ref_lo']}-{data['ref_hi']}",
            "abnormal_flag": "L" if data["value"] < data["ref_lo"]
                             else "H" if data["value"] > data["ref_hi"]
                             else "N"
        })

    return obx_segments
```

### Przykład importu do bazy danych HIS (PostgreSQL)

```python
async def import_scan_to_his(scan_result: dict, patient_id: str):
    """Zapisuje wyniki OCR do tabeli wyników HIS."""
    
    labs = scan_result["parsed_data"].get("labs", {})
    scan_id = scan_result["scan_id"]
    exam_date = scan_result["parsed_data"].get("patient", {}).get("exam_date")

    async with his_db.transaction():
        # Utwórz zlecenie badania
        order_id = await his_db.fetchval("""
            INSERT INTO lab_orders (patient_id, source, external_id, exam_date, status)
            VALUES ($1, 'ikzocr', $2, $3, 'completed')
            RETURNING id
        """, patient_id, scan_id, exam_date)

        # Zapisz wyniki parametrów
        for param, data in labs.items():
            await his_db.execute("""
                INSERT INTO lab_results
                    (order_id, param_code, value, unit, ref_lo, ref_hi, status)
                VALUES ($1, $2, $3, $4, $5, $6,
                    CASE WHEN $3 < $5 THEN 'low'
                         WHEN $3 > $6 THEN 'high'
                         ELSE 'normal' END)
            """, order_id, param, data["value"], data.get("unit"),
                data.get("ref_lo"), data.get("ref_hi"))
```

---

## 4. Eksport do CSV i import do Excela / bazy danych

### Pobieranie CSV przez API

```bash
# Jeden dokument
curl "https://api.ikzocr.pl/v1/documents/{scan_id}/export.csv" \
  -H "Authorization: Bearer mk_TwójKlucz" \
  -o wynik.csv

# Wszystkie dokumenty
curl "https://api.ikzocr.pl/v1/documents/export" \
  -H "Authorization: Bearer mk_TwójKlucz" \
  -o wszystkie_wyniki.csv
```

### Format CSV

```csv
scan_id,data_skanu,typ_dokumentu,pewnosc,pacjent,pesel,HGB,WBC,RBC,PLT,HCT,MCV
uuid-001,2026-07-15,morphology,0.92,ANNA KOWALSKA,XXXXXX*****,12.5,6.2,4.1,220,38.4,89.2
uuid-002,2026-07-16,morphology,0.88,JAN NOWAK,XXXXXX*****,15.2,7.8,4.8,310,44.1,91.0
```

### Import do PostgreSQL

```bash
# Bezpośredni import CSV do tabeli
docker compose exec -T postgres psql -U medyk -d medykocr -c "
COPY lab_import (scan_id, exam_date, doc_type, confidence, patient_name, pesel, HGB, WBC)
FROM STDIN WITH (FORMAT csv, HEADER true)
" < wyniki.csv
```

### Import do MySQL / MariaDB

```sql
LOAD DATA INFILE '/tmp/wyniki.csv'
INTO TABLE lab_import
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(scan_id, exam_date, doc_type, confidence, patient_name, pesel, @HGB, @WBC)
SET HGB = NULLIF(@HGB, ''), WBC = NULLIF(@WBC, '');
```

---

## 5. Przykłady kodu

### Python — pełny klient z retry i obsługą błędów

```python
import requests
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class IKZOCRClient:
    def __init__(self, api_key: str, base_url: str = "https://api.ikzocr.pl"):
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"
        self.base_url = base_url

    def scan(self, file_path: str | Path, retries: int = 3) -> dict:
        """Skanuje dokument z automatycznym retry."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Plik nie istnieje: {path}")

        for attempt in range(retries):
            try:
                with open(path, "rb") as f:
                    r = self.session.post(
                        f"{self.base_url}/v1/scan",
                        files={"file": (path.name, f)},
                        timeout=120
                    )
                r.raise_for_status()
                result = r.json()
                logger.info(f"Scan OK: {result['scan_id']} | {result['doc_type']} | confidence={result['confidence']:.2f}")
                return result
            except requests.Timeout:
                logger.warning(f"Timeout (próba {attempt+1}/{retries})")
                if attempt < retries - 1:
                    time.sleep(5 * (attempt + 1))
            except requests.HTTPError as e:
                if e.response.status_code == 429:
                    logger.error("Przekroczono limit skanów")
                    raise
                if e.response.status_code >= 500:
                    logger.warning(f"Błąd serwera (próba {attempt+1}/{retries}): {e}")
                    time.sleep(10)
                else:
                    raise
        raise RuntimeError(f"Nie udało się po {retries} próbach")

    def get_document(self, scan_id: str) -> dict:
        r = self.session.get(f"{self.base_url}/v1/documents/{scan_id}", timeout=10)
        r.raise_for_status()
        return r.json()

    def export_csv(self, scan_id: str) -> str:
        r = self.session.get(f"{self.base_url}/v1/documents/{scan_id}/export.csv", timeout=10)
        r.raise_for_status()
        return r.text

    def list_documents(self, limit: int = 50, offset: int = 0) -> list:
        r = self.session.get(
            f"{self.base_url}/v1/documents",
            params={"limit": limit, "offset": offset},
            timeout=10
        )
        r.raise_for_status()
        return r.json()


# Użycie
client = IKZOCRClient(api_key="mk_TwójKlucz")
result = client.scan("morfologia_pacjenta.jpg")

hgb = result["parsed_data"]["labs"].get("HGB", {})
print(f"HGB: {hgb.get('value')} {hgb.get('unit')}")

for alert in result.get("alerts", []):
    if alert["level"] == "critical":
        print(f"⚠️ KRYTYCZNY: {alert['message']}")
```

### PHP — przykład prostej integracji

```php
<?php

class IKZOCRClient {
    private string $apiKey;
    private string $baseUrl;

    public function __construct(string $apiKey, string $baseUrl = 'https://api.ikzocr.pl') {
        $this->apiKey  = $apiKey;
        $this->baseUrl = $baseUrl;
    }

    public function scan(string $filePath): array {
        $curl = curl_init();

        curl_setopt_array($curl, [
            CURLOPT_URL            => "{$this->baseUrl}/v1/scan",
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_HTTPHEADER     => ["Authorization: Bearer {$this->apiKey}"],
            CURLOPT_POSTFIELDS     => ['file' => new CURLFile($filePath)],
            CURLOPT_TIMEOUT        => 120,
        ]);

        $response = curl_exec($curl);
        $httpCode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        curl_close($curl);

        if ($httpCode !== 200) {
            throw new RuntimeException("IKZOCR error {$httpCode}: {$response}");
        }

        return json_decode($response, true);
    }
}

// Użycie
$client = new IKZOCRClient('mk_TwójKlucz');
$result = $client->scan('/var/upload/morfologia.jpg');

$hgb = $result['parsed_data']['labs']['HGB'] ?? null;
if ($hgb) {
    echo "HGB: {$hgb['value']} {$hgb['unit']}\n";
}
```

### Node.js / TypeScript

```typescript
import FormData from "form-data"
import fetch from "node-fetch"
import fs from "fs"

export class IKZOCRClient {
    constructor(
        private readonly apiKey: string,
        private readonly baseUrl = "https://api.ikzocr.pl"
    ) {}

    async scan(filePath: string): Promise<ScanResult> {
        const form = new FormData()
        form.append("file", fs.createReadStream(filePath))

        const res = await fetch(`${this.baseUrl}/v1/scan`, {
            method: "POST",
            headers: { Authorization: `Bearer ${this.apiKey}`, ...form.getHeaders() },
            body: form,
            signal: AbortSignal.timeout(120_000)
        })

        if (!res.ok) {
            const text = await res.text()
            throw new Error(`IKZOCR ${res.status}: ${text}`)
        }

        return res.json() as Promise<ScanResult>
    }

    async listDocuments(limit = 50, offset = 0): Promise<DocumentListItem[]> {
        const res = await fetch(
            `${this.baseUrl}/v1/documents?limit=${limit}&offset=${offset}`,
            { headers: { Authorization: `Bearer ${this.apiKey}` } }
        )
        if (!res.ok) throw new Error(`Error ${res.status}`)
        return res.json() as Promise<DocumentListItem[]>
    }
}

// Użycie
const client = new IKZOCRClient("mk_TwójKlucz")
const result = await client.scan("morfologia.jpg")
console.log(result.parsed_data.labs)
```

---

## 6. Integracja z aplikacją mobilną Flutter

```dart
// lib/src/services/ikzocr_service.dart

import 'dart:io';
import 'package:dio/dio.dart';

class IKZOCRService {
  final Dio _dio;
  final String apiKey;

  IKZOCRService({required this.apiKey, String baseUrl = 'https://api.ikzocr.pl'})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 120),
          headers: {'Authorization': 'Bearer $apiKey'},
        ));

  Future<Map<String, dynamic>> scanDocument(File file) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        file.path,
        filename: file.path.split('/').last,
      ),
    });

    final response = await _dio.post('/v1/scan', data: formData);
    return response.data as Map<String, dynamic>;
  }

  Future<List<dynamic>> listDocuments({int limit = 20}) async {
    final response = await _dio.get('/v1/documents', queryParameters: {'limit': limit});
    return response.data as List<dynamic>;
  }
}

// Użycie w widget/bloc:
final service = IKZOCRService(apiKey: 'mk_TwójKlucz');
final result  = await service.scanDocument(imageFile);
final hgb     = result['parsed_data']['labs']['HGB']?['value'];
```

---

## 7. Roadmap integracji

| Funkcja | Status | Planowane |
|---------|--------|-----------|
| REST API | ✅ Dostępne | — |
| Webhook (scan.completed) | ✅ Dostępne | — |
| CSV / TXT / MD export | ✅ Dostępne | — |
| HL7 FHIR R4 export | 🔄 Planowane | Q4 2026 |
| DICOM SR (structured report) | 🔄 Planowane | Q1 2027 |
| Python SDK (pip install ikzocr) | 🔄 Planowane | Q3 2026 |
| Node.js SDK (npm install ikzocr) | 🔄 Planowane | Q3 2026 |
| Zapier / Make.com connector | 💡 Pod rozważaniem | TBD |
| Direct EMR integrations | 💡 Pod rozważaniem | TBD |

Masz konkretną potrzebę integracyjną? Napisz: kontakt@ikzocr.pl
