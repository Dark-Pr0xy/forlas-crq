/**
 * Shared helpers for the Loss Exceedance Curve charts.
 *
 * `interpolateY` does log-space linear interpolation so a cursor between two
 * empirical samples reports a smooth exceedance value (used by the LEC tooltip).
 * `returnPeriod` turns an annual exceedance probability into a "1 in N years"
 * phrase.
 */

export function interpolateY(data: [number, number][], x: number): number {
  if (data.length === 0) return 0;
  if (x <= data[0][0]) return data[0][1];
  if (x >= data[data.length - 1][0]) return data[data.length - 1][1];
  let lo = 0;
  let hi = data.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (data[mid][0] <= x) lo = mid;
    else hi = mid;
  }
  const [x0, y0] = data[lo];
  const [x1, y1] = data[hi];
  if (x1 === x0) return y0;
  const t = (Math.log(x) - Math.log(x0)) / (Math.log(x1) - Math.log(x0));
  return y0 + (y1 - y0) * t;
}

/**
 * Resample a sorted-by-x curve to `points` samples uniformly spaced in log(x)
 * between the first and last x. Every y is interpolated in log-space.
 *
 * The engine samples the LEC evenly by RANK, which leaves the high-loss tail
 * sparse in x — the cursor then jumps between distant points. Densifying to a
 * uniform log-x grid means there's always a nearby point, so the line and the
 * tooltip both track the cursor smoothly across the whole range.
 */
export function densifyLogX(
  curve: [number, number][],
  points = 500,
): [number, number][] {
  const pos = curve.filter(([x]) => x > 0);
  if (pos.length < 2) return pos;
  const x0 = pos[0][0];
  const x1 = pos[pos.length - 1][0];
  if (x1 <= x0) return pos;
  const logMin = Math.log(x0);
  const logMax = Math.log(x1);
  const out: [number, number][] = [];
  for (let i = 0; i < points; i++) {
    const x = Math.exp(logMin + ((logMax - logMin) * i) / (points - 1));
    out.push([x, interpolateY(pos, x)]);
  }
  return out;
}

export function returnPeriod(p: number): string {
  if (p <= 0) return "—";
  if (p >= 1) return "every year";
  const years = 1 / p;
  if (years < 2) return "~ once a year";
  if (years < 10) return `1 in ${years.toFixed(1)} years`;
  if (years < 100) return `1 in ${Math.round(years)} years`;
  return `1 in ${Math.round(years).toLocaleString("en-AU")} years`;
}
