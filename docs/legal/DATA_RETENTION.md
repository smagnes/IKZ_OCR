# IKZOCR — Polityka retencji danych

## Okresy przechowywania

| Kategoria | Plan Starter | Plan Pro | Enterprise / On-Premise |
|-----------|-------------|---------|------------------------|
| Wyniki OCR (pola, alerty) | 12 miesięcy | 24 miesiące | Konfigurowalnie |
| Raw text (tekst surowy) | 12 miesięcy | 24 miesiące | Konfigurowalnie |
| Dane konta użytkownika | Czas umowy + 5 lat | Czas umowy + 5 lat | Czas umowy + 5 lat |
| Logi dostępu (IP, akcje) | 90 dni | 90 dni | 90 dni |
| Logi płatności | 5 lat (KSH) | 5 lat | 5 lat |
| Backupy bazy danych | 30 dni | 60 dni | 90 dni |
| Dane po usunięciu konta | 30 dni (backup) | 30 dni | 30 dni |

## Automatyczne usuwanie

System usuwa dane automatycznie po upływie okresu retencji:

```sql
-- Przykład: usunięcie skanów starszych niż 12 miesięcy (plan Starter)
DELETE FROM scans 
WHERE created_at < NOW() - INTERVAL '12 months'
  AND api_key_id IN (SELECT id FROM api_keys WHERE plan = 'starter');
```

Job uruchamiany codziennie o 03:00 UTC.

## Żądanie usunięcia danych (prawo do bycia zapomnianym)

Klient lub pacjent może zażądać usunięcia danych:
1. Email: rodo@ikzocr.pl z tematem "Usunięcie danych"
2. Podaj: adres email konta lub Scan ID
3. Termin realizacji: 30 dni (art. 17 RODO)

Po usunięciu konta wszystkie skany są usuwane w ciągu 30 dni (czas na ostatni backup rotacyjny).

## On-Premise

W instalacjach lokalnych retencja jest **wyłączną odpowiedzialnością klienta**. SZOP sp. z o.o. nie ma dostępu do danych. Zalecamy:
- Konfigurację automatycznego usuwania zgodnie z art. 5 ust. 1 lit. e) RODO (zasada minimalizacji)
- Dokumentację medyczną: min. 20 lat (art. 29 ust. 1 Ustawy o prawach pacjenta)
- Logi systemu: min. 90 dni (rekomendacja NIS2)
