// Formatting helpers shared across components/pages.

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const pct = v * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(digits)}%`;
}

export function fmtUsd(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

export function fmtShares(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Math.round(v).toLocaleString("en-US");
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" });
}

export function returnClass(v: number | null | undefined, beatMargin = 0.05): string {
  if (v === null || v === undefined) return "stamp-neutral";
  if (v > beatMargin) return "stamp-beat";
  if (v < -beatMargin) return "stamp-miss";
  return "stamp-neutral";
}

export function returnLabel(v: number | null | undefined, beatMargin = 0.05): string {
  if (v === null || v === undefined) return "N/A";
  if (v > beatMargin) return "Beat";
  if (v < -beatMargin) return "Miss";
  return "Flat";
}
