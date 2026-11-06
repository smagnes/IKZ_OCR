# IKZOCR — Service Level Objectives

Zdefiniowane przed pierwszą płatną umową. Jeśli nie możemy tych celów zmierzyć — mamy lukę w monitoringu.

---

## SLO produkcyjne

| Metryka | Cel (SLO) | Pomiar |
|---------|-----------|--------|
| Dostępność API (`/health`) | ≥ 99.5% miesięcznie | health-check co 2 min |
| Latencja OCR (PDF z tekstem) | p95 < 10s | `processing_time_ms` w bazie |
| Latencja OCR (obraz/skan) | p95 < 30s | `processing_time_ms` w bazie |
| Latencja API (non-OCR) | p99 < 500ms | nginx access log |
| Error rate (5xx) | < 1% requestów miesięcznie | nginx error log |
| Czas odpowiedzi panelu (LCP) | < 2.5s | Web Vitals (console.warn przy poor) |

---

## Error budget

99.5% dostępności miesięcznie = max **3h 36min downtime/miesiąc**.

Jeśli alert health-check pali się łącznie dłużej niż 3.5h w miesiącu — incydent do analizy.

---

## Co robimy gdy SLO jest przekroczone

- OCR p95 > 30s przez > 24h → sprawdzamy logi, szukamy wzorca (duże pliki? konkretny typ dokumentu?)
- Error rate > 1% → alert, sprawdzamy `docker logs medyk_ocr_api` i nginx
- Dostępność < 99.5% w miesiącu → post-mortem, wpis do `docs/legal/INCIDENT_LOG.md`

---

## Co obiecujemy klientom (SLA)

SLA to umowne SLO — to co wpisujemy do kontraktu. Nigdy nie obiecujemy więcej niż SLO minus bufor.

| Tier | Dostępność | OCR czas | Support |
|------|-----------|----------|---------|
| Starter | 99% | < 60s | email, 2 dni robocze |
| Pro | 99.5% | < 30s | email, 1 dzień roboczy |
| Enterprise | 99.9% | < 15s | dedykowany kontakt |

> **Uwaga**: 99.9% dostępności = max 43 min downtime/miesiąc. Nie oferuj Enterprise dopóki nie masz auto-restart, load balancera i redundancji bazy.

---

## Wymagania Jana Kurendy (benchmark z 11.2026)

Do spełnienia przed podpisaniem umowy z IKZ:
- ≥ 95% parametrów zgodnych z kontraktem na 20 anonimizowanych wynikach
- Obraz przetworzony w < 30s
- Zero retencji po stronie IKZOCR (opcja per klucz)
