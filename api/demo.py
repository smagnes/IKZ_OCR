"""Izolowane sesje demo: limiter zapytań per IP i ustalanie IP klienta.

Każdy gość demo dostaje własne, tymczasowe konto i klucz API (db.create_demo_account),
więc jego dokumenty są odseparowane tym samym filtrem api_key_id co u klientów.
Limiter działa w pamięci procesu — API startuje z jednym workerem uvicorn.
"""
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:
    """Okno przesuwne: maks. `max_hits` zdarzeń na klucz w ciągu `window_s` sekund."""

    def __init__(self, max_hits: int, window_s: int):
        self.max_hits = max_hits
        self.window_s = window_s
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str) -> bool:
        """Rejestruje zdarzenie. Zwraca False, gdy limit jest przekroczony."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window_s:
                q.popleft()
            if len(q) >= self.max_hits:
                return False
            q.append(now)
            # Sprzątanie pustych kluczy, żeby słownik nie rósł bez końca
            if len(self._hits) > 10_000:
                for k in [k for k, v in self._hits.items() if not v]:
                    del self._hits[k]
            return True

    def check(self, key: str, detail: str) -> None:
        if not self.hit(key):
            raise HTTPException(
                status_code=429,
                detail=detail,
                headers={"Retry-After": str(self.window_s)},
            )

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def client_ip(request: Request, trust_proxy: bool) -> str:
    """IP klienta. Za reverse proxy (nginx dopisuje IP na końcu X-Forwarded-For)
    bierzemy ostatni wpis — wcześniejsze może podać sam klient."""
    if trust_proxy:
        xff = request.headers.get("x-forwarded-for", "")
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]
        real = request.headers.get("x-real-ip")
        if real:
            return real.strip()
    return request.client.host if request.client else "unknown"
