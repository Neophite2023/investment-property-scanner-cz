from __future__ import annotations

import httpx

_eur_rate: float | None = None


def get_eur_rate() -> float:
    global _eur_rate
    if _eur_rate is not None:
        return _eur_rate

    try:
        resp = httpx.get("https://api.cnb.cz/cnbapi/exrates/daily?lang=EN", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for rate in data.get("rates", []):
            if rate.get("currencyCode") == "EUR":
                _eur_rate = rate["rate"] / rate.get("amount", 1)
                return _eur_rate
    except Exception:
        pass

    _eur_rate = 25.0
    return _eur_rate


def clear_cache() -> None:
    global _eur_rate
    _eur_rate = None
