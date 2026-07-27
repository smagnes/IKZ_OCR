# IKZOCR — Umowa o poziomie usług (SLA)

> Obowiązuje od: 2026-01-01  
> Dotyczy: usługi SaaS (panel.ikzocr.pl / api.ikzocr.pl)  
> On-Premise: SLA obejmuje wyłącznie dostarczone oprogramowanie, nie infrastrukturę klienta

## 1. Poziomy dostępności

| Plan | Gwarantowana dostępność | Dozwolony przestój/miesiąc |
|------|------------------------|---------------------------|
| Starter | Best effort (~99%) | Brak gwarancji |
| Pro | **99,5%** | ~3h 39min |
| Enterprise | **99,9%** | ~43min |

Dostępność mierzona jako: `(czas działania / całkowity czas) × 100%`  
Wyłączone z obliczeń: planowane okna serwisowe (z 24h wyprzedzeniem).

## 2. Czasy odpowiedzi API

| Operacja | P50 | P95 | P99 |
|----------|-----|-----|-----|
| `POST /v1/scan` (obraz < 5MB) | < 8s | < 20s | < 45s |
| `POST /v1/scan` (obraz 5–20MB) | < 20s | < 60s | < 120s |
| `GET /v1/documents` | < 200ms | < 500ms | < 1s |
| `GET /v1/documents/{id}` | < 100ms | < 300ms | < 500ms |
| Panel (ładowanie strony) | < 1s | < 2s | < 3s |

## 3. Planowane okna serwisowe

- Powiadomienie: **minimum 24h** przed pracami (email + status page)
- Preferowane okno: wtorek–czwartek, 02:00–06:00 CET
- Max. czas prac: 4h na sesję
- Awaryjne prace (krytyczny patch bezpieczeństwa): możliwe bez 24h wyprzedzenia

## 4. Wsparcie techniczne

| Plan | Kanał | Czas odpowiedzi (Krytyczny) | Czas odpowiedzi (Normalny) |
|------|-------|----------------------------|---------------------------|
| Starter | Email | 72h | 5 dni roboczych |
| Pro | Email + Slack | 24h | 2 dni robocze |
| Enterprise | Email + Slack + telefon | **4h** | 1 dzień roboczy |

**Priorytet Krytyczny** = system niedostępny lub utrata danych.  
**Priorytet Normalny** = degradacja funkcji, błędy nieblokujące.

Godziny wsparcia (Krytyczny): 24/7 dla Enterprise, godziny robocze dla pozostałych.  
Email wsparcia: support@ikzocr.pl

## 5. Kompensaty za niedotrzymanie SLA

Dla planów Pro i Enterprise — w przypadku niedotrzymania gwarantowanej dostępności:

| Faktyczna dostępność | Kredyt |
|----------------------|--------|
| 99,0% – 99,5% (Pro) / 99,5% – 99,9% (Ent.) | 10% opłaty miesięcznej |
| 98,0% – 99,0% | 25% opłaty miesięcznej |
| < 98,0% | 50% opłaty miesięcznej |

Kredyt przyznawany jako **obniżka kolejnej faktury** (nie zwrot gotówkowy).  
Maksymalny kredyt: 50% opłaty miesięcznej za dany miesiąc.

**Jak wnioskować o kredyt:** email na support@ikzocr.pl w ciągu 14 dni od incydentu z datą/godziną i opisem.

## 6. Wyłączenia SLA

SLA nie obejmuje przestojów wynikających z:
- Siły wyższej (klęski żywiołowe, ataki na infrastrukturę DNS/CDN, awarie dostawcy chmury)
- Działań lub zaniechań Klienta (błędna konfiguracja, przeciążenie po stronie Klienta)
- Planowanych okien serwisowych (z zachowaniem 24h powiadomienia)
- Incydentów bezpieczeństwa wymagających natychmiastowego działania
- Planu Starter (best effort)

## 7. Monitoring i transparentność

- Status systemu w czasie rzeczywistym: **status.ikzocr.pl** (planowane)
- Metryki wewnętrzne: Prometheus + Grafana (dla Administratora)
- Health check: `GET /health` → `{"status":"ok","version":"x.y.z"}`
- Historia incydentów: publikowana na status page po zamknięciu

## 8. Przegląd SLA

SLA przeglądany co 12 miesięcy. Zmiany komunikowane z 30-dniowym wyprzedzeniem.
