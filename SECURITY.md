# Security Policy

## Obsługiwane wersje

| Wersja | Wsparcie bezpieczeństwa |
|--------|------------------------|
| 0.3.x  | ✅ Aktywne wsparcie |
| 0.2.x  | ⚠️ Tylko krytyczne poprawki |
| < 0.2  | ❌ Brak wsparcia |

## Zgłaszanie podatności (Responsible Disclosure)

**Nie zgłaszaj podatności bezpieczeństwa publicznie przez GitHub Issues.**

Jeśli odkryłeś lukę bezpieczeństwa w IKZOCR, skontaktuj się z nami prywatnie:

**Email:** security@ikzocr.pl  
**Temat:** `[SECURITY] Krótki opis podatności`  
**Odpowiedź:** w ciągu 48 godzin roboczych

### Co uwzględnić w zgłoszeniu

- Opis podatności i jej potencjalny wpływ
- Kroki reprodukcji (proof of concept jeśli możliwe)
- Wersja IKZOCR której dotyczy
- Twoje dane kontaktowe (opcjonalnie — akceptujemy anonimowe zgłoszenia)

### Czego oczekiwać po zgłoszeniu

1. **48h** — potwierdzenie otrzymania zgłoszenia
2. **7 dni** — wstępna ocena ważności i zakresu
3. **90 dni** — wdrożenie poprawki (dla krytycznych podatności szybciej)
4. **Po patchu** — publiczne podziękowanie (jeśli wyrażasz zgodę)

Prosimy o nieujawnianie szczegółów podatności publicznie przed wdrożeniem poprawki.

## Znane obszary ryzyka

- System przetwarza dane medyczne — wszelkie podatności mogące prowadzić do wycieku danych zdrowotnych traktujemy jako krytyczne
- API uwierzytelnianie przez klucze Bearer — klucze należy traktować jak hasła

## Hall of Fame

Doceniamy odpowiedzialne zgłoszenia. Osoby które zgłosiły potwierdzone podatności znajdą się tutaj (za zgodą zgłaszającego).

*Brak zgłoszeń do tej pory.*

---

Kontakt bezpieczeństwa: security@ikzocr.pl
