# Izolacja demo — opis zmian i wdrożenie

Gałąź: `feat/demo-isolation`

## Problem (stan przed zmianą)

- Produkcja (`panel.ikzocr.pl/login`): przycisk „Wypróbuj demo” wywołuje `POST /auth/login`
  z `demo@ikzocr.pl` i hasłem zapisanym na sztywno w publicznym JS panelu. Wszyscy goście
  pracują na jednym koncie.
- Dokumenty w API są przypisane do **klucza API** (`scans.api_key_id`), nie do użytkownika.
  `/auth/login` nie zwraca klucza, więc panel używa klucza z `localStorage` albo domyślnego
  `NEXT_PUBLIC_API_KEY` / `mk_prod_demo123` (jawnie w bundlu JS). W efekcie wszyscy goście demo
  (i każdy, kto zna ten klucz) widzą te same dokumenty.
- Repo (`main`) zawiera starszą wersję panelu (fałszywy JWT generowany w przeglądarce),
  ale backend odpowiada produkcji (te same endpointy w `/openapi.json`).

## Rozwiązanie: tymczasowe konto na gościa

Wybrane zamiast trybu „bez zapisu”, bo izolacja wynika z istniejącego filtra `api_key_id`
we wszystkich endpointach dokumentów — nie trzeba przepisywać listy, szczegółów, eksportów
ani statystyk. Tryb sesyjny wymagałby osobnej ścieżki w każdym z nich.

| Element | Zachowanie |
|---|---|
| `POST /auth/demo` | Tworzy osobnego użytkownika `demo-<12 hex>@demo.ikzocr.invalid` i klucz `mk_demo_…` (plan `demo_guest`). Zwraca JWT (claim `demo: true`, wygasa razem z kontem) i klucz. Hasło losowe, nigdzie nie zwracane — zalogować się hasłem nie da. |
| Ważność | 24 h (`DEMO_TTL_HOURS`). Wygasły klucz jest odrzucany od razu (filtr `expires_at > NOW()`), niezależnie od sprzątania. |
| Limit | 10 skanów łącznie na sesję (`DEMO_SCANS_LIMIT`), nie resetuje się z początkiem miesiąca. |
| Sprzątanie | Przy starcie API i co 15 min (`DEMO_CLEANUP_INTERVAL_S`): usuwa wygasłe konta demo, ich klucze i wszystkie skany (jedna transakcja). Konta zwykłe nie są dotykane. |
| `POST /auth/demo/end` | Przycisk „Zakończ demo i usuń dane” w banerze i wylogowanie — kasuje dane od razu. |
| Blokady w API (nie tylko w UI) | 403 dla demo: `send-email`, nagłówek `X-IKZ-Silos-Id` (IKZ Mobile), webhook, tworzenie kluczy. Webhook nie jest wysyłany. `GET /v1/api-keys` pokazuje gościowi tylko jego klucz; zwykłym kluczom nie pokazuje kluczy demo. |
| Limity per IP (w pamięci, 1 worker) | 5 nowych sesji / h (`DEMO_SESSIONS_PER_IP_PER_HOUR`), 20 skanów / h łącznie ze wszystkich sesji z IP — też `/translate` (`DEMO_SCANS_PER_IP_PER_HOUR`), 60 zapytań / min (`DEMO_REQUESTS_PER_IP_PER_MINUTE`). IP = ostatni wpis `X-Forwarded-For` (`TRUST_PROXY_HEADERS=true`). |
| Stare konto | `POST /auth/login` dla `demo@ikzocr.pl` zwraca 403 (`BLOCKED_LOGIN_EMAILS`). |
| Panel | Baner „Wersja demo — nie wgrywaj dokumentów z danymi pacjentów” z czasem do wygaśnięcia; przyciski email wyłączone; „IKZ Mobile — wyłączone w demo”; klucz demo w osobnym `localStorage` (`ikzocr_demo_api_key`), więc nie nadpisuje klucza zwykłego konta; automatyczne wylogowanie po wygaśnięciu. |

Schemat: `db.ensure_schema()` przy starcie dodaje `is_demo`, `expires_at` do `users` i `api_keys`
(`ADD COLUMN IF NOT EXISTS`) oraz indeksy częściowe. Bez ręcznej migracji.

## Testy

```bash
api/run_tests.sh
```

Bez dostępu do Docker Hub można użyć lokalnego obrazu z Pythonem 3.11:
`TEST_IMAGE=ikzocr-test:latest api/run_tests.sh`. Wynik na tej gałęzi: 12 passed.

Uruchamia osobny kontener Postgres 15 i Python 3.11 (silnik OCR zaślepiony), po czym je usuwa.
Pokrycie (`api/tests/test_demo_isolation.py`): dwie sesje nie widzą swoich dokumentów (lista,
szczegóły, eksporty, usuwanie, statystyki, stary wspólny klucz); wygasła sesja jest odrzucana
i po czyszczeniu znika z bazy razem ze skanami, a dane zwykłego klienta zostają; aktywne sesje
przetrwają czyszczenie; „Zakończ demo”; limit skanów; blokady email / IKZ Mobile / webhook /
klucze; limity per IP (w tym próba podrobienia `X-Forwarded-For`); blokada logowania na stare konto.

## Wdrożenie (po akceptacji Sebastiana)

**Uwaga:** panel na produkcji to inny kod niż `panel/` w repo (polski UI, logowanie demo przez
`/auth/login`). Kodu produkcyjnego panelu nie ma w repo ani na GitHubie — jest tylko na serwerze
GCP w `~/ikzocr`. Zmiany w panelu trzeba tam przenieść ręcznie (krok 3).

1. **Kopia bazy** (Supabase → Database → Backups albo `pg_dump`) przed wdrożeniem.
2. **API** — na serwerze w `~/ikzocr`:
   - podmień `api/main.py`, `api/db.py`, dodaj `api/demo.py` z gałęzi (najpierw `diff` z wersją
     produkcyjną — jeśli produkcja ma lokalne zmiany, scal je, nie nadpisuj);
   - sprawdź, że nginx/Caddy przed API ustawia `X-Forwarded-For` (`proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`).
     Jeśli API jest wystawione bez proxy, ustaw `TRUST_PROXY_HEADERS=false` w `api/.env`,
     inaczej klient może podać dowolne IP i ominąć limity;
   - przebuduj i zrestartuj kontener API (np. `docker compose up -d --build ocr-api`);
   - w logach powinno nie być błędów `ensure_schema`; sprawdź `curl -X POST https://api.ikzocr.pl/auth/demo` → 200 z `token` i `api_key`.
3. **Panel** — w produkcyjnym `panel/src/app/login/page.tsx` zamień wywołanie
   `login("demo@ikzocr.pl", "demo2026ikz")` na `startDemo()` z `panel/src/lib/api.ts` w tej gałęzi.
   Przenieś też: `lib/auth.ts` (`DEMO_API_KEY`, `isDemo`, `logout`), `lib/api.ts`
   (`apiKeyHeaders`, `startDemo`, `endDemo`, blokady w `scanDocument`/`sendScanEmail`),
   `components/DemoBanner.tsx`, `ConditionalLayout.tsx`, `Sidebar.tsx` (wylogowanie demo),
   przyciski email / IKZ Mobile w stronie skanu i `MedicalResultView.tsx`.
   Przebuduj panel. Usuń hasło demo z kodu panelu.
4. **Stare wspólne konto** — od razu po wdrożeniu API:
   - zmień hasło `demo@ikzocr.pl` na losowe (jest publiczne w obecnym JS);
   - sprawdź, które klucze były używane przez gości demo, zanim cokolwiek usuniesz:
     ```sql
     SELECT k.id, k.key_prefix, k.name, k.user_id, COUNT(s.id) AS scans
     FROM api_keys k LEFT JOIN scans s ON s.api_key_id = k.id::text
     GROUP BY k.id ORDER BY scans DESC;
     ```
   - dokumenty wgrane przez gości na wspólne konto/klucz usuń po decyzji (mogą zawierać dane
     pacjentów): `DELETE FROM scans WHERE api_key_id = '<id klucza demo>';`
5. **Weryfikacja na produkcji**: dwie przeglądarki (lub okno prywatne) → „Wypróbuj demo” w obu →
   wgraj plik testowy (bez danych osobowych) w jednej → druga ma pustą listę „Dokumenty”.
   Baner widoczny, „Wyślij email” nieaktywny. „Zakończ demo i usuń dane” → wylogowanie.

Wycofanie: przywróć poprzednie obrazy API i panelu. Dodane kolumny są nieszkodliwe dla starego kodu.

## Poza zakresem tej zmiany (do osobnej decyzji)

- `mk_prod_demo123` jest w publicznym JS i jest kluczem domyślnym panelu dla każdego zalogowanego
  użytkownika bez klucza w `localStorage` — zwykli użytkownicy też mogą dzielić dokumenty. Zalecane:
  `/auth/login` zwraca/wydaje klucz użytkownika (albo dokumenty filtrowane po JWT), usunięcie fallbacku i rotacja klucza.
- `GET /v1/api-keys` zwraca wszystkie klucze wszystkich placówek każdemu posiadaczowi klucza;
  `PATCH /v1/api-keys/{id}/webhook` pozwala zmienić webhook cudzego klucza.
- `/v1/scan/local` i `/v1/translate/local` nie wymagają uwierzytelnienia.
- Domyślny `jwt_secret` w kodzie — upewnić się, że produkcja ma własny `JWT_SECRET`.
