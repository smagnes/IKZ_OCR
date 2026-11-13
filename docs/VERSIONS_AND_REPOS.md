# IKZOCR — wersje, repozytoria i stan lokalnego stacku

Stan na 2026-11-13. Dokument opisuje, które repozytorium jest czym, żeby nie mieszać produkcji z wersją lokalną/EDGE.

## Repozytoria

| Projekt | Repozytorium GitHub | Lokalnie | Rola |
|---|---|---|---|
| IKZOCR (produkcja / Cloud) | `smagnes/IKZ_OCR` | `~/medyk-ocr` (starsza linia MedykOCR), historia wspólna do commita z 2026-07 | Wersja produkcyjna na stronie. Nie dotykać z tej gałęzi roboczej. |
| IKZOCR Local (wersja robocza v2 / Dr Kiwi) | `smagnes/IKZOCR_local` | `~/ikzocr_local` | Wersja lokalna: silnik `claude` domyślnie, opcjonalnie Paddle, validator wyników, specyfikacja v2. |
| IKZ Mobile / EDGE | `smagnes/IKZ_mobile` | `~/ikz_mobile` (gałąź `ikzedge-clean`) | Aplikacja mobilna EDGE, OCR na urządzeniu. |

Uwaga: `ikzocr_test` to nazwa obrazu Dockera (`ikzocr-test:latest`) zbudowanego z `~/ikzocr_local`.
Nie jest osobnym kodem. Kod jest w repozytorium IKZOCR Local.

## Co jest w IKZOCR Local ponad produkcją

- `docs/KIWI_SPEC_v2.md` — specyfikacja prac v2 dla Dr Kiwi (27.10.2026).
- `api/ocr/validator.py` — walidator wyników OCR (172 linie, jeszcze niepodpięty, brak testów).
- `docker-compose.local.yml` — stack testowy: API + Postgres 15 + Redis 7, wybór silnika przez `OCR_ENGINE`.
- Gałąź `feature/v2-kiwi` — gałąź robocza v2.

## Lokalny stack Docker

Projekt compose: `ikzocr_local`, kontenery `ikzocr_test_api`, `ikzocr_test_postgres`, `ikzocr_test_redis`.

- Baza `medykocr` zawiera tylko dane testowe (2 klucze API, 0 użytkowników, 0 skanów). Można ją bezpiecznie odtworzyć z `init.sql`.
- Zdrowie API: PaddleOCR nie startuje (brak `libGL.so.1` w obrazie). Z silnikiem `claude` API działa.
- Sekrety (`.env.local`) nie są w repozytorium. Szablon zmiennych: `ANTHROPIC_API_KEY`, `OCR_ENGINE`.

## Surya

- Brak w tym repozytorium kodu Surya 2 ani osobnego modelu. W `api/ocr/parser.py` są tylko obejścia błędów kolumn starej Surya.
- Stary obraz `medyk/reg:surya-test` (rejestr `ikz-gl.ib2.eu`) jest wyeksportowany do `~/Downloads/surya.tar`.

## Do zrobienia

1. Sprawdzić, na którym commicie stoi produkcja i czy jej baza jest aktualna względem `IKZ_OCR`.
2. Dokumentacja EDGE vs Cloud: wspólne API, różne silniki OCR i miejsce przechowywania danych.
3. Podpiąć albo usunąć `validator.py`, dopisać testy.
4. Dodać `.env.local` do `.gitignore`.
5. Zastąpić token w adresie zdalnym credential helperem.
