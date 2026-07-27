# IKZOCR — Polityka obsługi incydentów

> Obowiązuje od: 2026-01-01  
> Właściciel: SZOP sp. z o.o.  
> Kontakt incydentowy: security@ikzocr.pl / support@ikzocr.pl

## 1. Klasyfikacja incydentów

### Poziom P1 — Krytyczny
- System całkowicie niedostępny (API + panel)
- Naruszenie bezpieczeństwa danych medycznych (breach)
- Utrata lub korupcja danych
- **Czas odpowiedzi: 15 minut · Czas rozwiązania: 4h**

### Poziom P2 — Wysoki
- Degradacja wydajności > 50% (znacznie wolniejsze skanowanie)
- Niedostępność jednego komponentu (np. tylko panel, API działa)
- Podejrzenie naruszenia bezpieczeństwa
- **Czas odpowiedzi: 1h · Czas rozwiązania: 8h**

### Poziom P3 — Średni
- Błędy sporadyczne, część funkcji niesprawna
- Problemy z eksportem, notyfikacjami
- **Czas odpowiedzi: 4h · Czas rozwiązania: 48h**

### Poziom P4 — Niski
- Kosmetyczne błędy UI
- Pytania techniczne
- **Czas odpowiedzi: 2 dni robocze**

## 2. Procedura obsługi incydentu

### Faza 1 — Wykrycie i klasyfikacja (0–15 min)

```
Źródła alertów:
  ├── Monitoring automatyczny (Prometheus → alert)
  ├── Zgłoszenie klienta (email/Slack)
  └── Wewnętrzne wykrycie (zespół)

Działania:
  1. Odbiór alertu / zgłoszenia
  2. Wstępna ocena skali (ile klientów dotyczy?)
  3. Przypisanie Incident Manager (IM)
  4. Klasyfikacja P1/P2/P3/P4
  5. Otwarcie kanału incydentowego (#incident-YYYY-MM-DD)
```

### Faza 2 — Komunikacja (15–30 min dla P1/P2)

- **Klienci dotknięci incydentem:** email z opisem i szacowanym czasem naprawy
- **Status page:** aktualizacja statusu (degraded / outage)
- **P1 breach:** powiadomienie CERT Polska w ciągu 24h (`incydent.cert.pl`)
- **P1 breach danych osobowych:** powiadomienie UODO w ciągu 72h (art. 33 RODO)

**Szablon komunikatu do klientów (P1):**
```
Temat: [IKZOCR] Incydent #XXX — [krótki opis]

Wykryliśmy problem wpływający na [opis zakresu].
Pracujemy nad rozwiązaniem. Szacowany czas przywrócenia: HH:MM.
Będziemy informować co [30/60] minut.

Przepraszamy za utrudnienia.
Zespół IKZOCR
```

### Faza 3 — Diagnoza i naprawa

```
Checklisty diagnostyczne:
  
  □ Sprawdź logi API:    docker compose logs ocr-api --since 1h
  □ Sprawdź logi DB:     docker compose logs postgres --since 1h
  □ Status kontenerów:   docker compose ps
  □ Użycie zasobów:      docker stats
  □ Health check:        curl http://localhost:8000/health
  □ Połączenie z bazą:   docker compose exec ocr-api python -c "import db; print('OK')"
  □ Redis:               docker compose exec redis redis-cli ping
  □ Dysk:                df -h
  □ RAM:                 free -h
```

**Eskalacja jeśli naprawa > 30 min (P1):** informuj klientów co 30 minut o postępie.

### Faza 4 — Rozwiązanie i komunikacja

1. Weryfikacja naprawy (smoke test wszystkich endpointów)
2. Email do klientów: potwierdzenie rozwiązania + czas trwania incydentu
3. Aktualizacja status page: `operational`
4. Zapis w rejestrze incydentów (`docs/incidents/YYYY-MM-DD-P1-opis.md`)

### Faza 5 — Post-mortem (dla P1 i P2)

Dokument post-mortem w ciągu **5 dni roboczych** od incydentu:

```markdown
## Incydent #XXX — Post-mortem

**Data:** YYYY-MM-DD  
**Czas trwania:** Xh Ymin  
**Poziom:** P1/P2  
**Dotknięci klienci:** N

### Co się stało
[Chronologia]

### Przyczyna główna (root cause)
[Techniczny opis]

### Co zadziałało dobrze
[Lista]

### Co nie zadziałało
[Lista]

### Działania naprawcze
| Akcja | Właściciel | Deadline |
|-------|-----------|----------|
| ...   | ...       | ...      |
```

## 3. Incydenty bezpieczeństwa (breach)

### Definicja naruszenia danych (RODO art. 4 pkt 12)

Naruszenie bezpieczeństwa prowadzące do przypadkowego lub niezgodnego z prawem:
- zniszczenia, utracenia, zmodyfikowania danych osobowych
- nieuprawnionego ujawnienia lub dostępu do danych

### Procedura breach

```
0–1h:   Izolacja zagrożonego komponentu (wyłącz jeśli konieczne)
1–4h:   Analiza zakresu naruszenia (które dane, ilu pacjentów)
4–24h:  Powiadomienie klientów (administrator danych → ich pacjenci)
24h:    Zgłoszenie do CERT Polska (incydent.cert.pl)
72h:    Zgłoszenie do UODO (jeśli wysokie ryzyko dla osób fizycznych)
30 dni: Raport końcowy + wdrożenie środków naprawczych
```

**Kontakt UODO:** uodo.gov.pl · ul. Stawki 2, 00-193 Warszawa  
**Kontakt CERT:** incydent.cert.pl

## 4. Kontakty alarmowe

| Rola | Kontakt |
|------|---------|
| Incident Manager (primary) | security@ikzocr.pl |
| Wsparcie techniczne | support@ikzocr.pl |
| CERT Polska | incydent.cert.pl |
| UODO | uodo.gov.pl |

## 5. Narzędzia i zasoby

- **Monitoring:** Grafana (`localhost:3001` lub VPN)
- **Logi:** `docker compose logs [service] --since Xh --follow`
- **Backup:** patrz [`docs/DEPLOYMENT.md`](DEPLOYMENT.md)
- **Rollback:** `docker compose pull [service] && docker compose up -d [service]`
- **Historia incydentów:** `docs/incidents/` (tworzone ręcznie po każdym P1/P2)
