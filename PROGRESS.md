# Investment Property Scanner CZ — Progress

## Goal
Prepísať scraper Sreality z nefunkčného REST API na scrapping cez `__NEXT_DATA__` z HTML search stránok.

## Solved Issues

### Seznam CMP consent redirect (root cause)
- `Accept: text/html,...` header v `httpx.Client` spúšťal CMP consent redirect na Sreality serveri (envoy proxy)
- Riešenie: odstrániť custom `Accept` header — ponechať iba `User-Agent` a `Accept-Language`
- httpx default `Accept: */*` neaktivuje CMP redirect

### City lookup case-sensitivity
- `get_region()` pridaná case-insensitive zhoda cez `casefold()`

### EUR/CZK prepočet
- Nový `backend/scanner/exchange.py` — fetching kurzu z CNB API (`api.cnb.cz`)
- Frontend: `lib/exchange.ts` — fetch kurzu, cache na 1h
- Ceny (predajná, nájom, cena/m²) zobrazené v CZK aj EUR
- Kurz sa získava počas SSR renderovania stránky (nie je uložený v DB)
- Aktuálny kurz: 1 EUR = ~24.165 CZK

## Status
- [x] REST API `/api/cs/v2/estates` — vracia 404, neriešiteľné
- [x] HTML search stránka — funguje s `__NEXT_DATA__` parsovaním
- [x] Paginácia (`?strana=N`) — funguje
- [x] Normalizácia — cena, plocha, layout, lokácia kompletné
- [x] Detail fetch — odstránený (vracia prázdny dict)
- [x] CMP consent obidený (odstránenie Accept headeru)
- [x] EUR/CZK prepočet — zobrazenie v CZK aj EUR

## Known Limitations
- Detail info (popis, vlastníctvo, kondícia, výťah, balkón) nie sú v NEXT_DATA — akceptované (~30% váha v scoringu)
- 1 listing z 88 nemá cenu (priceCzk=None) — korektne spracovaný ako `price=None, area=None`
- Konzola Windows cp1250 nevie zobraziť UTF-8 znaky (², ě, š...) — netýka sa logiky

## Relevant Files
- `backend/scanner/sreality.py` — hlavný scraper, NEXT_DATA parsing
- `backend/scanner/config.py` — mapovanie miest a regiónov
- `backend/scanner/pipeline.py` — orchestrácia scrapovania
- `backend/scanner/exchange.py` — fetching EUR/CZK kurzu z CNB API
- `frontend/src/lib/exchange.ts` — frontend fetch kurzu s cache
- `frontend/src/lib/format.ts` — `formatEur()` funkcia
- `frontend/src/app/page.tsx` — zobrazenie EUR cien
