/**
 * Central formatters. All monetary values are Australian Dollars (AUD).
 *
 * The breakpoints in `formatCurrencyAUD` match the spec in fix.md §2 and §1:
 *   - <1K        → A$0…A$999          (integer)
 *   - <100K      → A$1.0K…A$99.9K     (1 decimal, e.g. A$30.8K)
 *   - <1M        → A$100K…A$999K      (0 decimals, e.g. A$320K)
 *   - <1B        → A$1.0M…A$999.9M    (1 decimal, e.g. A$1.0M, A$100.0M)
 *   - <1T        → A$1.0B…A$999.9B    (1 decimal)
 *   - ≥1T        → A$1.0T+
 */

export const CURRENCY_PREFIX = "A$";

export function formatCurrencyAUD(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const sign = value < 0 ? "-" : "";
  const a = Math.abs(value);
  if (a < 1_000) return `${sign}${CURRENCY_PREFIX}${Math.round(a)}`;
  if (a < 100_000) return `${sign}${CURRENCY_PREFIX}${(a / 1_000).toFixed(1)}K`;
  if (a < 1_000_000) return `${sign}${CURRENCY_PREFIX}${Math.round(a / 1_000)}K`;
  if (a < 1_000_000_000) return `${sign}${CURRENCY_PREFIX}${(a / 1_000_000).toFixed(1)}M`;
  if (a < 1_000_000_000_000) return `${sign}${CURRENCY_PREFIX}${(a / 1_000_000_000).toFixed(1)}B`;
  return `${sign}${CURRENCY_PREFIX}${(a / 1_000_000_000_000).toFixed(1)}T`;
}

/** Full AUD integer with thousands separator — e.g. A$1,250,000. */
export function formatCurrencyAUDFull(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${CURRENCY_PREFIX}${Math.round(value).toLocaleString("en-AU")}`;
}

export const fmt = {
  money: formatCurrencyAUD,
  moneyFull: formatCurrencyAUDFull,
  pct(x: number | null | undefined, decimals = 1): string {
    if (x == null || !Number.isFinite(x)) return "—";
    return `${(x * 100).toFixed(decimals)}%`;
  },
  int(x: number | null | undefined): string {
    if (x == null || !Number.isFinite(x)) return "—";
    return Math.round(x).toLocaleString("en-AU");
  },
  date(s: string | null | undefined): string {
    if (!s) return "—";
    return new Date(s).toISOString().slice(0, 10);
  },
  /** Standard deviation count formatted with a sign, e.g. +1.42σ. */
  sigma(x: number | null | undefined, decimals = 2): string {
    if (x == null || !Number.isFinite(x)) return "—";
    const sign = x >= 0 ? "+" : "";
    return `${sign}${x.toFixed(decimals)}σ`;
  },
  /** Signed delta for Δ-from-mean style columns. */
  signedMoney(x: number | null | undefined): string {
    if (x == null || !Number.isFinite(x)) return "—";
    const sign = x >= 0 ? "+" : "-";
    return `${sign}${formatCurrencyAUD(Math.abs(x))}`;
  },
} as const;
