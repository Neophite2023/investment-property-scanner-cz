# Investment Property Scanner CZ

Automatizovaný systém na vyhľadávanie investičných bytov v ČR.

## Obsah

- `backend/`: Python worker na scraping, scoring a reporty.
- `frontend/`: Next.js PWA dashboard.
- `supabase/schema.sql`: databázová schéma.

## Spustenie backendu

```powershell
cd backend
python -m pip install -r requirements.txt
python -m scanner run-all
```

## Spustenie frontendu

```powershell
cd frontend
npm install
npm run dev
```

## Potrebné premenné

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Nasadenie

1. Nahraj `supabase/schema.sql` do Supabase SQL editoru.
2. Nastav secrets pre GitHub Actions.
3. Spusť workflow `Scan property listings`.

