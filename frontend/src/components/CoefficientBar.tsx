const FEATURE_LABELS: Record<string, string> = {
  num_distinct_insiders: "# distinct insiders",
  log_total_value: "log10($ purchased)",
  has_ceo_cfo: "CEO/CFO participated",
  sector_tech: "Sector: Technology",
  sector_healthcare: "Sector: Healthcare",
  sector_financial: "Sector: Financial Svcs",
};

export default function CoefficientBar({ feature, value, maxAbs }: { feature: string; value: number; maxAbs: number }) {
  const pct = maxAbs > 0 ? (Math.abs(value) / maxAbs) * 50 : 0;
  const positive = value >= 0;
  return (
    <div className="coef-bar-row">
      <span className="coef-bar-label">{FEATURE_LABELS[feature] ?? feature}</span>
      <div className="coef-bar-track">
        <div
          className="coef-bar-fill"
          style={{
            left: positive ? "50%" : `${50 - pct}%`,
            width: `${pct}%`,
            background: positive ? "var(--t-beat)" : "var(--t-miss)",
          }}
        />
        <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "var(--border-strong)" }} />
      </div>
      <span className="coef-bar-val">{value >= 0 ? "+" : ""}{value.toFixed(3)}</span>
    </div>
  );
}
