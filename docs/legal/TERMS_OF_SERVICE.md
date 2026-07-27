# Regulamin świadczenia usług IKZOCR

> Obowiązuje od: 2026-01-01

## 1. Definicje

- **Usługodawca** — SZOP sp. z o.o., operator systemu IKZOCR
- **Klient** — podmiot (placówka medyczna, firma) korzystający z systemu
- **Użytkownik** — osoba fizyczna posiadająca konto w panelu IKZOCR
- **System** — oprogramowanie IKZOCR (SaaS lub On-Premise)
- **Skan** — jednorazowe przetworzenie dokumentu przez silnik OCR

## 2. Zakres usługi

IKZOCR świadczy usługę automatycznego rozpoznawania i strukturyzowania danych z dokumentów medycznych (OCR). Usługa dostępna jest w modelu:
- **SaaS** — przez panel.ikzocr.pl
- **On-Premise** — oprogramowanie instalowane na infrastrukturze Klienta

## 3. Rejestracja i konto

- Konto zakładają wyłącznie podmioty uprawnione do przetwarzania dokumentacji medycznej
- Klient ponosi odpowiedzialność za bezpieczeństwo danych logowania
- Jedno konto = jedna placówka (chyba że plan przewiduje inaczej)

## 4. Prawa i obowiązki Klienta

Klient:
- Jest administratorem danych medycznych przetwarzanych przez IKZOCR (IKZOCR działa jako podmiot przetwarzający)
- Zobowiązuje się używać systemu zgodnie z prawem, w tym RODO i ustawą o prawach pacjenta
- Nie może udostępniać kluczy API osobom nieuprawnionym
- Ponosi odpowiedzialność za dane przesyłane do systemu

## 5. Prawa i obowiązki Usługodawcy

Usługodawca:
- Zapewnia dostępność systemu zgodnie z SLA (Starter: best effort, Pro: 99,5%, Enterprise: 99,9%)
- Nie przegląda treści dokumentów medycznych przesyłanych przez Klienta
- Zobowiązuje się do zachowania poufności danych
- Może przeprowadzać prace konserwacyjne (z 24h wyprzedzeniem, poza godzinami szczytu)

## 6. Limity i płatności

- Limity skanów według planu (patrz `docs/PRICING.md`)
- Przekroczenie limitu: rozliczenie nadlimitowe na koniec okresu
- Brak płatności: zawieszenie konta po 14 dniach, usunięcie danych po 60 dniach
- Faktury VAT wystawiane do 7. dnia następnego miesiąca

## 7. Dane i RODO

Strony zawierają odrębną **Umowę Powierzenia Przetwarzania Danych** (DPA) zgodną z art. 28 RODO. DPA jest integralną częścią regulaminu i dostępna na żądanie.

## 8. Odpowiedzialność

- Usługodawca nie ponosi odpowiedzialności za decyzje medyczne podjęte na podstawie wyników OCR
- Wyniki OCR są orientacyjne — wymagają weryfikacji przez uprawniony personel medyczny
- Maksymalna odpowiedzialność Usługodawcy ograniczona jest do wartości opłat wniesionych przez Klienta w ciągu ostatnich 3 miesięcy

## 9. Rozwiązanie umowy

- Klient: może wypowiedzieć umowę w dowolnym momencie (bez opłat za następny okres przy zachowaniu 30-dniowego okresu wypowiedzenia)
- Usługodawca: może wypowiedzieć umowę z 30-dniowym wyprzedzeniem lub natychmiast w przypadku naruszenia regulaminu

## 10. Zmiany regulaminu

O zmianach regulaminu informujemy emailem z 30-dniowym wyprzedzeniem. Dalsze korzystanie z usługi po tym terminie oznacza akceptację zmian.

## 11. Prawo właściwe

Regulamin podlega prawu polskiemu. Spory rozstrzygane przez sąd właściwy dla siedziby Usługodawcy.

---

Kontakt: kontakt@ikzocr.pl
