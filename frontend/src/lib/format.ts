export function formatCzk(value: number | null | undefined) {
  if (value == null) return "N/A";
  return new Intl.NumberFormat("cs-CZ", {
    style: "currency",
    currency: "CZK",
    maximumFractionDigits: 0
  }).format(value);
}

export function formatEur(value: number | null | undefined) {
  if (value == null) return null;
  return new Intl.NumberFormat("sk-SK", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0
  }).format(value);
}

export function formatNumber(value: number | null | undefined, suffix = "") {
  if (value == null) return "N/A";
  return `${new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: 1 }).format(value)}${suffix}`;
}

export function formatPercent(value: number | null | undefined) {
  if (value == null) return "N/A";
  const sign = value > 0 ? "+" : "";
  return `${sign}${new Intl.NumberFormat("cs-CZ", { maximumFractionDigits: 1 }).format(value)} %`;
}

