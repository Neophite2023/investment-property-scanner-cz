create extension if not exists pgcrypto;

create table if not exists public.listings (
  id uuid primary key default gen_random_uuid(),
  listing_id text not null unique,
  source text not null default 'sreality',
  transaction_type text not null check (transaction_type in ('sale', 'rent')),
  title text not null,
  url text not null,
  city text,
  district text,
  street text,
  price integer,
  area numeric,
  price_per_m2 numeric,
  layout text,
  ownership text,
  floor integer,
  floors_total integer,
  condition text,
  elevator boolean,
  balcony boolean,
  terrace boolean,
  cellar boolean,
  parking boolean,
  garage boolean,
  latitude numeric,
  longitude numeric,
  description text,
  first_seen timestamptz not null default now(),
  last_seen timestamptz not null default now(),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.listing_snapshots (
  id uuid primary key default gen_random_uuid(),
  listing_id text not null references public.listings(listing_id) on delete cascade,
  raw_data jsonb not null,
  price integer,
  title text,
  description text,
  content_hash text not null,
  captured_at timestamptz not null default now()
);

create table if not exists public.price_history (
  id uuid primary key default gen_random_uuid(),
  listing_id text not null references public.listings(listing_id) on delete cascade,
  price integer not null,
  captured_at timestamptz not null default now()
);

create table if not exists public.market_statistics (
  id uuid primary key default gen_random_uuid(),
  city text not null,
  district text not null default 'unknown',
  layout text not null,
  transaction_type text not null default 'sale',
  median_price_per_m2 numeric,
  average_price_per_m2 numeric,
  p25_price_per_m2 numeric,
  p75_price_per_m2 numeric,
  sample_size integer not null default 0,
  updated_at timestamptz not null default now(),
  unique(city, district, layout, transaction_type)
);

create table if not exists public.rental_statistics (
  id uuid primary key default gen_random_uuid(),
  city text not null,
  district text not null default 'unknown',
  layout text not null,
  average_rent integer,
  median_rent integer,
  average_rent_per_m2 numeric,
  sample_size integer not null default 0,
  updated_at timestamptz not null default now(),
  unique(city, district, layout)
);

create table if not exists public.scores (
  id uuid primary key default gen_random_uuid(),
  listing_id text not null unique references public.listings(listing_id) on delete cascade,
  investment_score integer not null,
  confidence_score integer not null,
  yield_score integer not null,
  price_score integer not null,
  location_score integer not null,
  condition_score integer not null,
  liquidity_score integer not null,
  risk_penalty integer not null default 0,
  estimated_rent integer,
  estimated_gross_yield numeric,
  market_difference_percent numeric,
  deal_type text not null,
  reasons jsonb not null default '[]'::jsonb,
  risks jsonb not null default '[]'::jsonb,
  next_action text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.reports (
  id uuid primary key default gen_random_uuid(),
  report_date date not null unique,
  new_listings_count integer not null default 0,
  price_drop_count integer not null default 0,
  report_json jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists public.watchlist (
  id uuid primary key default gen_random_uuid(),
  listing_id text not null references public.listings(listing_id) on delete cascade,
  status text not null default 'new' check (
    status in ('new', 'interesting', 'dismissed', 'contacted', 'viewing_scheduled', 'offer_made', 'archived')
  ),
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(listing_id)
);

create table if not exists public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  endpoint text not null unique,
  p256dh text not null,
  auth text not null,
  user_agent text,
  created_at timestamptz not null default now()
);

create index if not exists listings_search_idx on public.listings(city, district, layout, transaction_type, active);
create index if not exists listings_score_idx on public.scores(investment_score desc, confidence_score desc);
create index if not exists price_history_listing_time_idx on public.price_history(listing_id, captured_at desc);
create index if not exists snapshots_listing_time_idx on public.listing_snapshots(listing_id, captured_at desc);

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace function public.preserve_listing_first_seen()
returns trigger
language plpgsql
as $$
begin
  new.first_seen = old.first_seen;
  return new;
end;
$$;

drop trigger if exists listings_touch_updated_at on public.listings;
create trigger listings_touch_updated_at
before update on public.listings
for each row execute function public.touch_updated_at();

drop trigger if exists listings_preserve_first_seen on public.listings;
create trigger listings_preserve_first_seen
before update on public.listings
for each row execute function public.preserve_listing_first_seen();

drop trigger if exists scores_touch_updated_at on public.scores;
create trigger scores_touch_updated_at
before update on public.scores
for each row execute function public.touch_updated_at();

drop trigger if exists watchlist_touch_updated_at on public.watchlist;
create trigger watchlist_touch_updated_at
before update on public.watchlist
for each row execute function public.touch_updated_at();

create or replace function public.count_price_drops_today(target_date date)
returns integer
language sql
stable
as $$
  with ordered as (
    select
      listing_id,
      price,
      captured_at,
      lag(price) over (partition by listing_id order by captured_at) as previous_price
    from public.price_history
    where captured_at >= target_date::timestamptz
       or captured_at >= (target_date::timestamptz - interval '3 days')
  )
  select count(*)::integer
  from ordered
  where captured_at::date = target_date
    and previous_price is not null
    and price < previous_price;
$$;

alter table public.listings enable row level security;
alter table public.scores enable row level security;
alter table public.market_statistics enable row level security;
alter table public.rental_statistics enable row level security;
alter table public.reports enable row level security;
alter table public.watchlist enable row level security;
alter table public.push_subscriptions enable row level security;

drop policy if exists "public read listings" on public.listings;
create policy "public read listings" on public.listings for select using (true);

drop policy if exists "public read scores" on public.scores;
create policy "public read scores" on public.scores for select using (true);

drop policy if exists "public read market statistics" on public.market_statistics;
create policy "public read market statistics" on public.market_statistics for select using (true);

drop policy if exists "public read rental statistics" on public.rental_statistics;
create policy "public read rental statistics" on public.rental_statistics for select using (true);

drop policy if exists "public read reports" on public.reports;
create policy "public read reports" on public.reports for select using (true);

