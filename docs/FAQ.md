# IKZOCR — Najczęściej zadawane pytania (FAQ)

## Spis treści

- [Ogólne](#ogólne)
- [Bezpieczeństwo i dane medyczne](#bezpieczeństwo-i-dane-medyczne)
- [Instalacja i wdrożenie](#instalacja-i-wdrożenie)
- [Jak działa OCR](#jak-działa-ocr)
- [Jakość wyników](#jakość-wyników)
- [Plany i cennik](#plany-i-cennik)
- [Integracje](#integracje)
- [Wsparcie techniczne](#wsparcie-techniczne)

---

## Ogólne

### Czym jest IKZOCR?

IKZOCR to platforma do automatycznego rozpoznawania i strukturyzowania danych z dokumentów medycznych (wyniki laboratoryjne, morfologie, epikryzy, zwolnienia lekarskie). System skanuje dokument i zwraca dane w formacie JSON, CSV lub Markdown — gotowe do importu do innych systemów.

### Dla kogo jest IKZOCR?

Dla placówek medycznych, laboratoriów, firm medtech i systemów HIS/LIS które chcą automatycznie przetwarzać dokumentację medyczną zamiast przepisywać ją ręcznie.

### Czy IKZOCR zastępuje lekarza lub diagnostę?

Nie. IKZOCR to narzędzie pomocnicze do automatyzacji przepisywania danych. Wyniki OCR wymagają weryfikacji przez uprawniony personel medyczny. System wyraźnie oznacza poziom pewności każdego odczytu.

### W jakich językach działa OCR?

Głównie polski i angielski. Silnik Surya obsługuje 90+ języków, ale parametry medyczne i wyrażenia regularne parsera są zoptymalizowane pod polskie dokumenty medyczne.

---

## Bezpieczeństwo i dane medyczne

### Czy dane medyczne wychodzą z naszego serwera?

**W wersji On-Premise: nie.** Cały system (OCR, baza danych, panel) działa na Twojej infrastrukturze. Dane nigdy nie opuszczają Twojej sieci.

**W wersji SaaS:** dokumenty są przesyłane do naszych serwerów w UE (szyfrowanie TLS 1.3), przetwarzane i przechowywane przez okres określony planem (12–24 miesiące). Szczegóły: [`docs/legal/DATA_RETENTION.md`](legal/DATA_RETENTION.md).

### Czy IKZOCR jest zgodny z RODO?

Tak. SZOP sp. z o.o. pełni rolę podmiotu przetwarzającego (art. 28 RODO). Z każdym klientem podpisujemy Umowę Powierzenia Przetwarzania Danych (DPA). Szczegóły: [`docs/legal/RODO.md`](legal/RODO.md).

### Jak chronione są dane pacjentów?

- Szyfrowanie w transmisji: TLS 1.3
- Szyfrowanie w spoczynku: AES-256
- PESEL przechowywany w bazie w formie zamaskowanej (`XXXXXX*****`)
- Klucze API przechowywane jako hash SHA-256 — nigdy w plaintext
- Pełny opis: [`docs/SECURITY_POLICY.md`](SECURITY_POLICY.md)

### Czy system jest zgodny z NIS2?

Tak, wdrożone środki bezpieczeństwa zgodne z art. 21 dyrektywy NIS2. Szczegóły i tabela statusu zgodności: [`docs/NIS2_COMPLIANCE.md`](NIS2_COMPLIANCE.md).

### Kto ma dostęp do naszych dokumentów?

W wersji SaaS — wyłącznie automatyczne procesy OCR. Pracownicy SZOP sp. z o.o. nie przeglądają treści dokumentów medycznych klientów. W wersji On-Premise — nikt poza Twoją organizacją.

### Jak długo przechowywane są dane?

| Plan | Wyniki OCR | Dane konta |
|------|-----------|-----------|
| Starter | 12 miesięcy | Czas umowy + 5 lat |
| Pro | 24 miesiące | Czas umowy + 5 lat |
| Enterprise / On-Premise | Konfigurowalnie | Czas umowy + 5 lat |

Po upływie okresu retencji dane są automatycznie usuwane. Szczegóły: [`docs/legal/DATA_RETENTION.md`](legal/DATA_RETENTION.md).

---

## Instalacja i wdrożenie

### Jakie są wymagania sprzętowe dla On-Premise?

Minimum:
- CPU: 4 vCPU (x86_64)
- RAM: 8 GB (16 GB zalecane)
- Dysk: 50 GB SSD (100 GB zalecane)
- System: Ubuntu 22.04 LTS
- Docker 24+, Docker Compose 2.20+

Z GPU (opcjonalnie): NVIDIA z 4 GB VRAM — skraca czas skanowania z ~30s do ~5s.

### Jak wygląda instalacja?

Instalacja trwa ok. 30–60 minut. Pełna instrukcja krok po kroku: [`docs/DEPLOYMENT.md`](DEPLOYMENT.md). W skrócie:

```bash
git clone https://github.com/smagnes/IKZ_OCR.git
cd IKZ_OCR
cp api/.env.example api/.env
# Edytuj .env
docker compose up -d
```

### Czy potrzebuję dostępu do internetu na serwerze?

Przy pierwszym uruchomieniu — tak (pobranie modeli AI ~1.5 GB z HuggingFace). Po pobraniu system działa w pełni offline.

### Jak działają aktualizacje w On-Premise?

Automatycznie przez Watchtower — serwis sprawdza co 24h czy jest nowy obraz Docker i restartuje kontenery. Dane w bazie PostgreSQL są bezpieczne — Watchtower nie dotyka volumów. Ręcznie: `docker compose pull && docker compose up -d`. Szczegóły: [`docs/UPGRADE_GUIDE.md`](UPGRADE_GUIDE.md).

### Czy instalacja wymaga połączenia z siecią zewnętrzną po wdrożeniu?

Nie. System działa w pełni offline po pierwszym uruchomieniu. Watchtower do aktualizacji wymaga dostępu do Docker Hub — można go wyłączyć i aktualizować ręcznie.

### Czy można zainstalować na Windows?

Oficjalnie wspieramy Ubuntu 22.04 LTS. Docker Desktop na Windows powinien działać, ale nie jest testowany i nie obejmuje go wsparcie techniczne.

---

## Jak działa OCR

### Jaki silnik OCR jest używany?

[Surya OCR](https://github.com/VikParuchuri/surya) — otwartoźródłowy silnik AI oparty na modelach Transformer, zoptymalizowany pod dokumenty wielojęzyczne i złożony układ strony (tabele, kolumny).

### Dlaczego Surya, a nie Tesseract?

Tesseract słabo radzi sobie z tabelarycznym układem wyników laboratoryjnych — wykrywa tekst w złej kolejności. Surya wykrywa układ strony i pozwala nam odtworzyć kolejność kolumn w tabelach.

### Jak IKZOCR identyfikuje parametry laboratoryjne (HGB, WBC itp.)?

Przez dopasowanie zakresu referencyjnego. Każdy parametr ma charakterystyczny zakres (np. HGB kobiety: 12.0–16.0 g/dL). IKZOCR szuka tych zakresów w tekście i na tej podstawie identyfikuje parametr — nie przez rozpoznanie tekstu nazwy. Metoda jest odporna na błędy OCR w nazwach parametrów.

### Co jeśli OCR się myli?

System podaje poziom pewności (confidence) dla każdego odczytu. Wartości poniżej 0.8 są oznaczane jako wymagające weryfikacji. Alerty medyczne (np. anemia, leukocytoza) generowane są tylko dla parametrów z wystarczającą pewnością.

### Jakie formaty plików są obsługiwane?

- Zdjęcia: JPEG, PNG, TIFF
- Dokumenty: PDF (pierwsza strona)
- Maksymalny rozmiar: 20 MB

---

## Jakość wyników

### Jaka jest dokładność OCR?

Dla dobrej jakości skanów (min. 200 DPI, dobre oświetlenie): 90–97% pewność. Dla zdjęć z telefonu przy słabym oświetleniu: 70–85%. System podaje confidence score dla każdego dokumentu.

### Co wpływa na jakość rozpoznawania?

**Pozytywnie:** wysokie DPI (300+), poziome ustawienie dokumentu, dobre oświetlenie, czysty druk (nie ręczne pismo).

**Negatywnie:** nieostre zdjęcie, mocny cień, obrót dokumentu >15°, ręczne dopiski, pomięty papier.

### Czy IKZOCR obsługuje ręczne pismo?

Częściowo — drukowane litery tak, kursywa słabo. Wyniki badań laboratoryjnych są zazwyczaj drukowane, więc to rzadki problem.

### Czy system obsługuje dokumenty wielostronicowe?

Aktualnie przetwarzana jest pierwsza strona PDF lub cały obraz. Obsługa batch (wiele stron) jest w roadmapie.

---

## Plany i cennik

### Jakie plany są dostępne?

| Plan | Cena | Skany/miesiąc |
|------|------|--------------|
| Starter | 199 PLN/mies. | 200 |
| Pro | 499 PLN/mies. | 1 000 |
| Enterprise | Indywidualnie | 5 000+ |
| On-Premise | Od 8 900 PLN/rok | Nielimitowane |

Pełny cennik: [`docs/PRICING.md`](PRICING.md).

### Co się dzieje po przekroczeniu limitu skanów?

Skanowanie jest zablokowane do końca okresu rozliczeniowego, lub możliwe jest rozliczenie nadlimitowe (stawka per skan). Klient jest informowany emailem przy 80% i 100% wykorzystania limitu.

### Czy jest darmowy trial?

Tak — skontaktuj się z nami (kontakt@ikzocr.pl) po token demo z 20 bezpłatnymi skanami.

### Czy można zmienić plan w trakcie okresu rozliczeniowego?

Upgrade — tak, od razu. Downgrade — od następnego okresu rozliczeniowego.

---

## Integracje

### Czy IKZOCR ma API?

Tak — pełne REST API z uwierzytelnianiem przez klucze Bearer. Dokumentacja: [`docs/API.md`](API.md).

### Jak zintegrować z własnym systemem HIS/LIS?

Przez REST API lub webhook. Po skanowaniu IKZOCR może wysłać wynik na Twój endpoint (webhook). Szczegóły: [`docs/INTEGRATIONS.md`](INTEGRATIONS.md).

### Czy jest SDK lub biblioteka kliencka?

Aktualnie nie ma oficjalnego SDK. API jest proste — wystarczy jeden request POST z plikiem i nagłówkiem Bearer. Przykłady w Python, curl i TypeScript: [`docs/API.md`](API.md).

### Czy IKZOCR obsługuje HL7/FHIR?

Eksport w formacie FHIR jest w roadmapie. Aktualnie wyniki dostępne jako JSON, CSV, Markdown i TXT.

---

## Wsparcie techniczne

### Jak zgłosić błąd?

- GitHub Issues: https://github.com/smagnes/IKZ_OCR/issues (użyj szablonu Bug Report)
- Email: support@ikzocr.pl
- Klienci Pro/Enterprise: dedykowany kanał Slack

### Jakie są godziny wsparcia?

| Plan | Godziny | Czas odpowiedzi (krytyczny) |
|------|---------|----------------------------|
| Starter | 9–17 pon–pt | 72h |
| Pro | 9–17 pon–pt | 24h |
| Enterprise | 24/7 | 4h |

### Gdzie znaleźć dokumentację techniczną?

- Architektura systemu: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md)
- Przewodnik dewelopera: [`docs/DEVELOPER.md`](DEVELOPER.md)
- Referencja API: [`docs/API.md`](API.md)
- Deployment: [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)

### Kto produkuje IKZOCR?

SZOP sp. z o.o. — polska firma technologiczna specjalizująca się w rozwiązaniach IT dla sektora medycznego.  
Email: kontakt@ikzocr.pl
