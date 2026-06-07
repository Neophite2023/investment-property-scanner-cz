let cachedRate: number | null = null;
let cachedAt = 0;
const CACHE_TTL = 3600_000; // 1 hour

export async function getEurRate(): Promise<number> {
  const now = Date.now();
  if (cachedRate != null && now - cachedAt < CACHE_TTL) {
    return cachedRate;
  }
  try {
    const res = await fetch("https://api.cnb.cz/cnbapi/exrates/daily?lang=EN", {
      next: { revalidate: 3600 },
    });
    const data: { rates: Array<{ currencyCode: string; rate: number; amount: number }> } = await res.json();
    for (const rate of data.rates) {
      if (rate.currencyCode === "EUR") {
        cachedRate = rate.rate / (rate.amount || 1);
        cachedAt = now;
        return cachedRate;
      }
    }
  } catch {
    // fallback
  }
  return 25.0;
}
