import { Building2, ExternalLink, Filter, Gauge, Home, TrendingDown } from "lucide-react";
import type { ReactNode } from "react";
import { formatCzk, formatEur, formatNumber, formatPercent } from "@/lib/format";
import { getEurRate } from "@/lib/exchange";
import { getSupabaseClient } from "@/lib/supabase";

type Listing = {
  listing_id: string;
  title: string;
  url: string;
  city: string | null;
  district: string | null;
  price: number | null;
  area: number | null;
  price_per_m2: number | null;
  layout: string | null;
  first_seen: string;
  floor: number | null;
  floors_total: number | null;
  condition: string | null;
  ownership: string | null;
  balcony: boolean | null;
  terrace: boolean | null;
  cellar: boolean | null;
  parking: boolean | null;
  elevator: boolean | null;
  description: string | null;
};

type ScoreRow = {
  listing_id: string;
  investment_score: number;
  confidence_score: number;
  estimated_rent: number | null;
  estimated_gross_yield: number | null;
  market_difference_percent: number | null;
  deal_type: string;
  reasons: string[];
  risks: string[];
  next_action: string;
  listings: Listing | null;
};

type ReportRow = {
  new_listings_count: number;
  price_drop_count: number;
};

type SearchParams = {
  city?: string;
  layout?: string;
  minScore?: string;
};

export default async function Dashboard({ searchParams }: { searchParams: SearchParams }) {
  const supabase = getSupabaseClient();
  if (!supabase) {
    return <SetupState />;
  }

  const eurRate = await getEurRate();

  const minScore = Number(searchParams.minScore || 70);
  let query = supabase
    .from("scores")
    .select("*,listings(*)")
    .gte("investment_score", minScore)
    .order("investment_score", { ascending: false })
    .limit(30);

  const { data: scoreData } = await query;
  const rows = ((scoreData || []) as ScoreRow[]).filter((row) => {
    const listing = row.listings;
    if (!listing) return false;
    if (searchParams.city && listing.city !== searchParams.city) return false;
    if (searchParams.layout && listing.layout !== searchParams.layout) return false;
    return true;
  });

  const { data: reportData } = await supabase
    .from("reports")
    .select("new_listings_count,price_drop_count")
    .order("report_date", { ascending: false })
    .limit(1)
    .maybeSingle<ReportRow>();

  const { count: watchedCount } = await supabase
    .from("listings")
    .select("listing_id", { count: "exact", head: true })
    .eq("transaction_type", "sale")
    .eq("active", true);

  const topScore = rows[0]?.investment_score ?? 0;

  return (
    <main className="min-h-screen">
      <header className="border-b border-line bg-paper">
        <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-moss">
                <Building2 size={18} />
                Investment Property Scanner CZ
              </div>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal text-ink">
                Investičné byty Brno, Zlín a Olomouc
              </h1>
            </div>
          </div>

          <form className="grid gap-3 rounded-md border border-line bg-white p-3 md:grid-cols-[1fr_1fr_1fr_auto]">
            <label className="text-xs font-medium uppercase tracking-normal text-ink/60">
              Mesto
              <select name="city" defaultValue={searchParams.city || ""} className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm text-ink">
                <option value="">Všetky</option>
                <option value="Brno">Brno</option>
                <option value="Zlín">Zlín</option>
                <option value="Olomouc">Olomouc</option>
              </select>
            </label>
            <label className="text-xs font-medium uppercase tracking-normal text-ink/60">
              Dispozícia
              <select name="layout" defaultValue={searchParams.layout || ""} className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm text-ink">
                <option value="">Všetky</option>
                {["1+kk", "1+1", "2+kk", "2+1", "3+kk", "3+1"].map((layout) => (
                  <option key={layout} value={layout}>{layout}</option>
                ))}
              </select>
            </label>
            <label className="text-xs font-medium uppercase tracking-normal text-ink/60">
              Min. skóre
              <input name="minScore" type="number" min="0" max="100" defaultValue={minScore} className="mt-1 h-10 w-full rounded-md border border-line bg-white px-3 text-sm text-ink" />
            </label>
            <button className="inline-flex h-10 items-center justify-center gap-2 self-end rounded-md bg-moss px-4 text-sm font-medium text-white">
              <Filter size={18} />
              Filtrovať
            </button>
          </form>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="metric-grid grid gap-3">
          <Metric icon={<Home size={20} />} label="Nové byty dnes" value={String(reportData?.new_listings_count ?? 0)} />
          <Metric icon={<TrendingDown size={20} />} label="Poklesy cien" value={String(reportData?.price_drop_count ?? 0)} />
          <Metric icon={<Gauge size={20} />} label="TOP skóre" value={`${topScore}/100`} />
          <Metric icon={<Building2 size={20} />} label="Sledované inzeráty" value={String(watchedCount ?? 0)} />
        </div>

        <div className="mt-6 overflow-hidden rounded-md border border-line bg-white">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-lg font-semibold">TOP investičné príležitosti</h2>
          </div>
          <div className="divide-y divide-line">
            {rows.length === 0 ? (
              <div className="px-4 py-8 text-sm text-ink/60">
                Zatiaľ nie sú dostupné žiadne byty pre zvolené filtre.
              </div>
            ) : (
              rows.map((row) => <Opportunity key={row.listing_id} row={row} eurRate={eurRate} />)
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-md border border-line bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="text-sm text-ink/60">{label}</div>
        <div className="text-steel">{icon}</div>
      </div>
      <div className="mt-3 text-2xl font-semibold text-ink">{value}</div>
    </div>
  );
}

function Opportunity({ row, eurRate }: { row: ScoreRow; eurRate: number }) {
  const listing = row.listings;
  if (!listing) return null;

  const priceEur = listing.price != null ? Math.round(listing.price / eurRate) : null;
  const ppmEur = listing.price_per_m2 != null ? Math.round(listing.price_per_m2 / eurRate) : null;
  const rentEur = row.estimated_rent != null ? Math.round(row.estimated_rent / eurRate) : null;

  return (
    <article className="grid gap-4 px-4 py-4 lg:grid-cols-[1fr_220px]">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-md bg-moss px-2 py-1 text-xs font-semibold text-white">{row.investment_score}/100</span>
          <span className="rounded-md bg-steel px-2 py-1 text-xs font-semibold text-white">Confidence {row.confidence_score}</span>
          <span className="text-sm font-medium text-wine">{row.deal_type}</span>
        </div>
        <h3 className="mt-3 text-lg font-semibold">{listing.title}</h3>
        <p className="mt-1 text-sm text-ink/60">
          {[listing.city, listing.district, listing.layout].filter(Boolean).join(" - ")}
        </p>
        <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Info label="Cena" value={formatCzk(listing.price)} secondary={formatEur(priceEur)} />
          <Info label="Plocha" value={formatNumber(listing.area, " m²")} />
          <Info label="Cena/m²" value={formatCzk(listing.price_per_m2)} secondary={formatEur(ppmEur)} />
          <Info label="Pod trhom" value={formatPercent(row.market_difference_percent)} />
          <Info label="Odhad nájmu" value={formatCzk(row.estimated_rent)} secondary={formatEur(rentEur)} />
          <Info label="Hrubý výnos" value={formatPercent(row.estimated_gross_yield)} />
        </div>
        <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Info label="Stav" value={listing.condition || "—"} />
          <Info label="Vlastníctvo" value={listing.ownership || "—"} />
          <Info label="Poschodie" value={listing.floor != null ? (listing.floors_total != null ? `${listing.floor}. / ${listing.floors_total}.` : `${listing.floor}.`) : "—"} />
          <Info label="Výťah" value={yn(listing.elevator)} />
          <Info label="Balkón" value={yn(listing.balcony)} />
          <Info label="Terasa" value={yn(listing.terrace)} />
          <Info label="Pivnica" value={yn(listing.cellar)} />
          <Info label="Parkovanie" value={yn(listing.parking)} />
        </div>
        {listing.description ? (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-xs font-medium uppercase tracking-normal text-moss">Popis nehnuteľnosti</summary>
            <p className="mt-2 whitespace-pre-wrap text-ink/70">{listing.description}</p>
          </details>
        ) : null}
        {(row.reasons?.length || row.risks?.length) ? (
          <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
            <TextList title="Dôvody" items={row.reasons || []} />
            <TextList title="Riziká" items={row.risks || []} />
          </div>
        ) : null}
      </div>
      <div className="flex flex-col justify-between gap-3 rounded-md border border-line bg-paper p-3">
        <p className="text-sm text-ink/70">{row.next_action}</p>
        <a className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-ink px-3 text-sm font-medium text-white" href={listing.url} target="_blank" rel="noopener noreferrer">
          <ExternalLink size={18} />
          Otvoriť inzerát
        </a>
      </div>
    </article>
  );
}

function Info({ label, value, secondary }: { label: string; value: string; secondary?: string | null }) {
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-normal text-ink/50">{label}</div>
      <div className="mt-1 font-semibold">{value}</div>
      {secondary != null && (
        <div className="text-xs text-ink/40">{secondary}</div>
      )}
    </div>
  );
}

function TextList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-normal text-ink/50">{title}</div>
      <ul className="mt-1 space-y-1 text-ink/70">
        {items.slice(0, 3).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function yn(value: boolean | null): string {
  if (value === true) return "Áno";
  if (value === false) return "Nie";
  return "—";
}

function SetupState() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-paper px-4">
      <section className="max-w-xl rounded-md border border-line bg-white p-6">
        <h1 className="text-2xl font-semibold">Chýba konfigurácia Supabase</h1>
        <p className="mt-3 text-sm text-ink/70">
          Nastav vo frontende premenné `NEXT_PUBLIC_SUPABASE_URL` a `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
        </p>
      </section>
    </main>
  );
}
