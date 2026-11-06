# IKZOCR — Procedura obsługi incydentu bezpieczeństwa

> Ostatnia aktualizacja: 2026-11-06  
> Właściciel: Sebastian Magnes (SZOP sp. z o.o.)

---

## Co to jest incydent

Incydent to każde zdarzenie które mogło naruszyć poufność, integralność lub dostępność danych osobowych. Zalicza się tu między innymi:

- nieautoryzowany dostęp do systemu lub bazy danych
- wyciek danych — przez atak, błąd konfiguracji lub przypadkowe ujawnienie
- utrata danych (skasowanie, awaria bez backupu)
- dostęp osoby nieuprawnionej do danych medycznych pacjentów
- przejęcie konta użytkownika lub klucza API

Zasada: jeśli nie jesteś pewny czy to incydent — traktuj to jak incydent.

---

## Zegar 72h — od momentu wykrycia, nie od potwierdzenia

Art. 33 RODO wymaga zgłoszenia do UODO w ciągu **72 godzin od wykrycia** naruszenia, jeśli może ono powodować ryzyko dla praw i wolności osób fizycznych. Zegar biegnie od momentu kiedy dowiedziałeś się o podejrzeniu — nie od potwierdzenia.

Jeśli 72h minie bez pełnego zbadania — zgłaszasz z tym co masz i uzupełniasz raport po czasie. UODO to akceptuje. Brak zgłoszenia nie jest akceptowany.

---

## Procedura krok po kroku

### Godzina 0 — wykrycie

1. Zapisz czas wykrycia (data, godzina, kto zgłosił, skąd informacja)
2. Zrób snapshot logów zanim cokolwiek zatrzymasz: `docker logs medyk_ocr_api > /tmp/incident_$(date +%Y%m%d_%H%M).log`
3. Oceń czy incydent trwa aktywnie — jeśli tak, izolujesz najpierw

### Izolacja (jeśli atak trwa)

```bash
# Zablokuj ruch do API tymczasowo przez nginx
sudo systemctl stop nginx

# Albo tylko zatrzymaj kontener API
docker stop medyk_ocr_api

# NIE usuwaj kontenerów ani logów — to dowody
```

### Godzina 0-4 — ocena zasięgu

Odpowiedz na pytania:
- Jakie dane były dostępne? (dokumenty OCR, dane kont, logi)
- Ile rekordów jest potencjalnie naruszonych?
- Czy dane opuściły system (exfiltration) czy tylko dostęp był nieautoryzowany?
- Jakie konta/klucze API mogły być skompromitowane?

```bash
# Sprawdź logi nginx — szukaj anomalii (masowe requesty, dziwne IP, 200 na /openapi.json)
sudo grep -v "panel.ikzocr.pl" /var/log/nginx/access.log | tail -500

# Sprawdź logi API
docker logs medyk_ocr_api --since 48h 2>&1 | grep -E "ERROR|WARNING|401|403|500"

# Sprawdź aktywne połączenia
sudo ss -tnp
```

### Godzina 4-24 — decyzja o zgłoszeniu do UODO

**Zgłaszasz do UODO jeśli:**
- naruszenie dotyczy danych osobowych (imię, PESEL, wyniki badań)
- istnieje ryzyko dla praw lub wolności osób (dyskryminacja, szkoda finansowa, naruszenie tajemnicy medycznej)

**Możesz nie zgłaszać jeśli:**
- dane były zaszyfrowane i klucz nie wyciekł
- naruszenie nie dotyczyło danych osobowych (np. tylko logi techniczne)
- ryzyko dla osób fizycznych jest "mało prawdopodobne"

W razie wątpliwości — zgłaszasz. Niezgłoszenie jest gorsze niż nadgorliwość.

### Zgłoszenie do UODO

Formularz online: **https://uodo.gov.pl/pl/83/155**

Wymagane informacje:
- Opis charakteru naruszenia (co się stało, skąd wiemy)
- Kategorie i przybliżona liczba osób, których dane dotyczą
- Kategorie i przybliżona liczba rekordów danych
- Prawdopodobne konsekwencje naruszenia
- Środki podjęte lub proponowane w celu zaradzenia naruszeniu

Jeśli nie masz wszystkich danych w ciągu 72h — zgłaszasz to co masz i dopisujesz.

### Powiadomienie użytkowników (art. 34 RODO)

Wymagane jeśli naruszenie "może powodować wysokie ryzyko" — tzn. realnie może zaszkodzić konkretnym osobom. Przy danych medycznych próg jest niski.

Treść powiadomienia musi zawierać:
- co się stało (bez technikaliów, zrozumiale)
- jakie dane zostały naruszone
- jakie kroki podjąłeś
- co użytkownik może zrobić (zmiana hasła, alert na PESEL itp.)
- kontakt do nas

Wyślij mailem do wszystkich których dotyczy. Zachowaj kopię wysłanych wiadomości.

---

## Rotacja sekretów po incydencie

Jeśli podejrzewasz że jakikolwiek sekret wyciekł — rotujesz wszystko, nie tylko ten jeden.

```bash
# Nowy JWT_SECRET
openssl rand -hex 32

# Na VM — zmień w ~/ikzocr/api/.env i zrestartuj kontener
# Efekt: wszystkie istniejące sesje użytkowników wygasają natychmiast

# Klucze API klientów — wygeneruj nowe w Supabase / panelu admina
# Stare dezaktywuj przez: UPDATE api_keys SET is_active = false WHERE ...

# Klucze dostępowe do infrastruktury (SSH, GCP) — zmień w GCP Console
```

---

## Dokumentacja incydentu — zachowaj zawsze

Niezależnie od tego czy zgłaszałeś do UODO czy nie, prowadź rejestr. RODO wymaga dokumentowania wszystkich naruszeń (art. 33 ust. 5) — nawet tych które nie wymagały zgłoszenia.

Plik: `docs/legal/INCIDENT_LOG.md` (nie wrzucać do publicznego repo)

Każdy wpis zawiera:
- datę wykrycia i datę zamknięcia
- opis incydentu
- zasięg (jakie dane, ile rekordów, ile osób)
- podjęte działania
- czy zgłoszono do UODO (jeśli tak — numer zgłoszenia)
- czy powiadomiono użytkowników

---

## Kontakty

| Rola | Kontakt |
|------|---------|
| Właściciel procedury | Sebastian Magnes — smgraphic4u@gmail.com |
| UODO zgłoszenia online | https://uodo.gov.pl/pl/83/155 |
| UODO telefon | +48 22 531 03 00 |
| CERT Polska (cyberataki) | https://incydent.cert.pl |
