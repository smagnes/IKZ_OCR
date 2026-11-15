# IKZOCR — Polityka ochrony danych osobowych (RODO)

> Dokument zgodny z RODO (Rozporządzenie UE 2016/679) oraz UODO (Ustawa z dnia 10 maja 2018 r.)  
> Ostatnia aktualizacja: 2026-11-06

## 1. Administrator danych

**KONKLUDI MED PROSTA SPÓŁKA AKCYJNA**  
ul. Czesława Miłosza 51/36  
80-126 Gdańsk  
NIP: 5833479868  
KRS: 0001040347  
Email: rodo@ikzocr.pl

## 2. Inspektor Ochrony Danych

IOD: [DO WYZNACZENIA]  
Email: iod@ikzocr.pl

## 3. Kategorie przetwarzanych danych

System IKZOCR przetwarza następujące kategorie danych:

### Dane zwykłe
- Dane konta użytkownika (imię, nazwisko, email, nazwa placówki)
- Dane rozliczeniowe (NIP, adres, historia płatności)
- Dane logów systemowych (adres IP, timestamp, ID sesji)

### Dane szczególnych kategorii (art. 9 RODO — dane dotyczące zdrowia)
- Dane pacjentów wyciągane z dokumentów medycznych:
  - Imię i nazwisko
  - PESEL (przechowywany w formie zamaskowanej: `XXXXXX*****`)
  - Data urodzenia
  - Wyniki badań laboratoryjnych
  - Diagnoza, leki, zabiegi

**Podstawa prawna przetwarzania danych zdrowotnych:** art. 9 ust. 2 lit. h) RODO — przetwarzanie niezbędne do celów profilaktyki zdrowotnej lub medycyny pracy, diagnozy medycznej, zapewnienia opieki zdrowotnej lub leczenia, na podstawie prawa Unii lub prawa państwa członkowskiego.

## 4. Cel i podstawa prawna przetwarzania

| Cel | Podstawa prawna |
|-----|-----------------|
| Świadczenie usługi OCR | art. 6 ust. 1 lit. b) RODO (wykonanie umowy) |
| Fakturowanie i rozliczenia | art. 6 ust. 1 lit. c) RODO (obowiązek prawny) |
| Bezpieczeństwo systemu | art. 6 ust. 1 lit. f) RODO (prawnie uzasadniony interes) |
| Marketing (za zgodą) | art. 6 ust. 1 lit. a) RODO (zgoda) |
| Przetwarzanie danych zdrowotnych | art. 9 ust. 2 lit. h) RODO |

## 5. Retencja danych

| Kategoria danych | Okres przechowywania |
|-----------------|----------------------|
| Wyniki OCR (skany) | Starter: 12 mies. / Pro: 24 mies. / Enterprise: konfigurowalnie |
| Dane konta użytkownika | Czas trwania umowy + 5 lat (obowiązki podatkowe) |
| Logi systemowe | 90 dni |
| Dane rozliczeniowe | 5 lat (wymogi podatkowe) |
| Dane po usunięciu konta | 30 dni (backup), następnie trwałe usunięcie |

## 6. Przekazywanie danych

### Architektura przetwarzania

IKZOCR przetwarza dokumenty medyczne na własnej infrastrukturze KONKLUDI MED PSA zlokalizowanej w Polsce (GCP, region europe-central2). Obraz dokumentu trafia na serwer Konkludi, gdzie następuje anonimizacja danych osobowych pacjenta (PESEL, imię, nazwisko, adres), a następnie zanonimizowany tekst jest przekazywany do zewnętrznego serwisu AI w celu ekstrakcji struktury badań.

**Dane osobowe pacjentów nie są przekazywane do zewnętrznych podmiotów** — do serwisu AI przesyłane są wyłącznie zanonimizowane wyniki badań (wartości liczbowe, nazwy parametrów, jednostki, zakresy referencyjne).

**Podmioty przetwarzające (podprocesory):**

| Podmiot | Rola | Lokalizacja | Dane medyczne |
|---------|------|-------------|---------------|
| Supabase Ireland Ltd. | Baza danych (PostgreSQL) | UE (Frankfurt) | Tak — wyniki OCR, dane kont |
| Google Cloud Platform (GCP) | Hosting serwera API | UE (Warszawa, europe-central2) | Tak — wszystkie dane w transmisji i spoczynku |
| Zewnętrzny serwis przetwarzania AI | Ekstrakcja struktury badań z tekstu | UE/USA — [WERYFIKACJA DPA] | Nie — wyłącznie dane zanonimizowane |
| Przelewy24 / Stripe | Płatności | UE | Nie — tylko dane rozliczeniowe |

Z każdym podmiotem przetwarzającym podpisana jest umowa powierzenia przetwarzania danych (DPA) zgodna z art. 28 RODO.

> ⚠️ **TODO (przed pierwszym kontraktem szpitalnym):** Podpisać DPA z dostawcą serwisu AI oraz zweryfikować lokalizację przetwarzania. Jeśli serwer AI zlokalizowany poza EOG — wymagane standardowe klauzule umowne (SCC).

### W wersji On-Premise
Dane **nie opuszczają** infrastruktury klienta. Administrator (Konkludi Med PSA) nie ma dostępu do danych medycznych klientów na instalacjach lokalnych.

## 7. Prawa osób, których dane dotyczą

Każda osoba, której dane przetwarza placówka używająca IKZOCR, ma prawo do:

- **Dostępu** do swoich danych (art. 15 RODO)
- **Sprostowania** nieprawidłowych danych (art. 16 RODO)
- **Usunięcia** danych ("prawo do bycia zapomnianym") (art. 17 RODO)
- **Ograniczenia** przetwarzania (art. 18 RODO)
- **Przeniesienia** danych (art. 20 RODO)
- **Sprzeciwu** wobec przetwarzania (art. 21 RODO)

Wnioski należy kierować na: rodo@ikzocr.pl  
Odpowiedź: w ciągu 30 dni od otrzymania wniosku.

## 8. Bezpieczeństwo danych

Stosowane środki techniczne i organizacyjne:
- Szyfrowanie danych w spoczynku (AES-256)
- Szyfrowanie transmisji (TLS 1.3)
- Maskowanie PESEL w bazie danych
- Kontrola dostępu oparta na rolach (RBAC)
- Logi audytu (kto, kiedy, jaki dokument)
- Regularne kopie zapasowe (backup szyfrowany)
- Polityka haseł (min. 12 znaków, MFA dla administratorów)

## 9. Naruszenia ochrony danych

W przypadku naruszenia:
1. Konkludi Med PSA zgłosi naruszenie do UODO w ciągu 72 godzin (art. 33 RODO)
2. Poinformuje osoby, których naruszenie dotyczy, jeśli ryzyko jest wysokie (art. 34 RODO)
3. Przeprowadzi postępowanie wyjaśniające i wdroży środki naprawcze

## 10. Kontakt

W sprawach RODO: rodo@ikzocr.pl  
Skarga do organu nadzorczego: Urząd Ochrony Danych Osobowych (uodo.gov.pl)
