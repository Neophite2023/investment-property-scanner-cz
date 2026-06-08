# Investment Property Scanner CZ — Progress

## Goal
Prepísať scraper Sreality z nefunkčného REST API na scrapping cez `__NEXT_DATA__` z HTML search stránok, nasadiť CI/CD a pridať EUR prepočet.

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

### Sreality detail URLs
- REST API URL formát `/detail/{trans}/{cat}/-/-/{id}` vracia 404
- Riešenie: extrahovať URL z HTML `<a href="/detail/...">` počas scrapovania
- Fallback: ak URL nie je v HTML (historické listingy), zostrojiť z locality dát (city+district+street+layout)
- Slugifikácia: odstránenie diakritiky, lowercase, nahradenie medzier pomlčkami

### Supabase upsert 500
- Batch 260+ rows v jednom requeste padal na 500 Internal Server Error
- Riešenie: rozdeliť na dávky po 50 rows

## Status
- [x] REST API `/api/cs/v2/estates` — vracia 404, neriešiteľné
- [x] HTML search stránka — funguje s `__NEXT_DATA__` parsovaním
- [x] Paginácia (`?strana=N`) — funguje
- [x] Normalizácia — cena, plocha, layout, lokácia kompletné
- [x] Detail fetch — odstránený (vracia prázdny dict)
- [x] CMP consent obidený (odstránenie Accept headeru)
- [x] EUR/CZK prepočet — zobrazenie v CZK aj EUR
- [x] Vercel deploy — frontend live
- [x] Sreality detail URLs — opravené (HTML extrakcia + fallback z locality)

## Known Limitations
- Detail info (popis, vlastníctvo, kondícia, výťah, balkón) nie sú v NEXT_DATA — akceptované (~30% váha v scoringu)
- 15 listingov má stále `/-/-/` URL (chýba layout alebo neexistujú na Sreality)
- Safari na iPhone: `target="_blank"` nemusí fungovať korektne — pridané `rel="noopener noreferrer"`
- Konzola Windows cp1250 nevie zobraziť UTF-8 znaky (², ě, š...) — netýka sa logiky

## 2026-06-08
- **Vercel deploy**: Frontend live na `frontend-one-kappa-13.vercel.app`
- **Supabase env vars**: Nastavené `NEXT_PUBLIC_SUPABASE_URL` a `NEXT_PUBLIC_SUPABASE_ANON_KEY` vo Verceli
- **Web Push**: Odstránené prázdne tlačidlo (bol to iba vizuálny placeholder)
- **Sreality URLs**: Opravené — scraper extrahuje URL z HTML `href="/detail/..."`; fallback cez `_construct_url()` z city+district+street+layout
- **URL migrácia**: 783/798 listingov v DB má funkčné URL (iba 15 so starým `/-/-/` formátom)
- **Batch upsert**: Rozdelený na dávky po 50 rows (fix 500 error)
- **`@next/swc-win32-x64-msvc`**: Presunutý do `optionalDependencies` pre build na Verceli (Linux)
- **Pipeline run**: 63 sale + 197 rent listingov, 388 scoringov, report OK
- **CI/CD**: GitHub Actions scan beží 7× denne; pipeline spustená manuálne

## Relevant Files
- `backend/scanner/sreality.py` — hlavný scraper, NEXT_DATA parsing + URL extrakcia/konštrukcia
- `backend/scanner/config.py` — mapovanie miest a regiónov
- `backend/scanner/pipeline.py` — orchestrácia scrapovania
- `backend/scanner/exchange.py` — fetching EUR/CZK kurzu z CNB API
- `backend/scanner/supabase.py` — REST klient pre Supabase (upsert s batchovaním)
- `frontend/src/lib/exchange.ts` — frontend fetch kurzu s cache
- `frontend/src/lib/format.ts` — `formatCzk()`, `formatEur()`
- `frontend/src/app/page.tsx` — dashboard, EUR ceny, Web Push odstránený
- `frontend/package.json` — optionalDependencies pre SWC
- `.github/workflows/scan.yml` — CI/CD pipeline
