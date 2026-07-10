import { useEffect, useState } from "react";
import { api } from "../api";
import type { MetaResponse, ModelInfo } from "../types";
import CoefficientBar from "../components/CoefficientBar";

export default function Methodology() {
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [model, setModel] = useState<ModelInfo | null>(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    api.model().then(setModel).catch(() => {});
  }, []);

  const maxAbsCoef = model?.coefficients_standardized
    ? Math.max(...Object.values(model.coefficients_standardized).map((v) => Math.abs(v)))
    : 1;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Methodology</h1>
          <p className="page-desc">
            How a cluster-buy event is detected, how forward returns are computed, and exactly
            what the logistic regression is and isn't — laid out plainly so nothing here is a
            black box.
          </p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-head"><h2>1. Cluster detection</h2></div>
          <div className="card-body">
            <ol className="methodology-list">
              <li>Start from every SEC Form 4 non-derivative transaction with <code>TRANS_CODE = &apos;P&apos;</code> (open-market/private purchase) and <code>TRANS_ACQUIRED_DISP_CD = &apos;A&apos;</code> (acquired) — the standard definition of an insider buying their own company&apos;s stock with their own money.</li>
              <li>For each ticker, sort its purchases by date. Anchor a 30-calendar-day window at the first unclustered transaction.</li>
              <li>Pull in every later transaction for that ticker within 30 days of the anchor. If the window contains purchases from <strong>2 or more distinct insiders</strong> (by CIK), it&apos;s a cluster-buy event.</li>
              <li>Emit the event and advance past every transaction it consumed — windows never overlap, so no transaction is double-counted into two events.</li>
              <li>Clusters with combined purchase value under $1,000,000 are dropped as noise.</li>
            </ol>
            <p className="mut" style={{ fontSize: 11.5 }}>
              This is a simple, auditable rule, not a statistical clustering algorithm — every
              event traces back to the exact transactions that produced it.
            </p>
          </div>
        </div>

        <div className="card">
          <div className="card-head"><h2>2. Event study / abnormal return</h2></div>
          <div className="card-body">
            <ol className="methodology-list">
              <li>The event &quot;anchor&quot; date is the date of the <strong>last</strong> qualifying transaction in the cluster — the date the cluster condition was first satisfied.</li>
              <li>Forward cumulative return is computed for the ticker and for SPY at +30/+60/+90 calendar days from the anchor, using the nearest available trading-day close.</li>
              <li><strong>Abnormal return = ticker return − SPY return</strong> over the same window. This is a market-adjusted return, the simplest standard event-study construction (no beta/risk adjustment — see Limitations).</li>
              <li>A cluster &quot;beats the benchmark&quot; if its 90-day abnormal return exceeds <strong>+{meta ? (meta.beat_margin * 100).toFixed(0) : 5}pp</strong>.</li>
            </ol>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-head">
          <h2>3. Logistic regression — why it isn&apos;t a black box</h2>
          <span className="hint">{model?.trained ? `n = ${model.n_samples}` : "not trained"}</span>
        </div>
        <div className="card-body">
          {model?.trained ? (
            <>
              <p className="event-summary" style={{ marginBottom: 14 }}>
                A single logistic regression predicts whether a cluster beats SPY by more than
                5 percentage points within 90 days, from four interpretable inputs: number of
                distinct insiders, log10(total dollar value purchased), whether a CEO/CFO
                participated (vs. only directors/other officers/10%-owners), and sector. No
                hidden layers, no ensembling — every coefficient below is the model in full.
                Features are standardized, so bar length is directly comparable across features.
              </p>
              {Object.entries(model.coefficients_standardized ?? {}).map(([f, v]) => (
                <CoefficientBar key={f} feature={f} value={v} maxAbs={maxAbsCoef} />
              ))}
              <div className="kpi-row" style={{ marginTop: 16 }}>
                <div className="kpi-tile">
                  <div className="kpi-label">Base rate</div>
                  <div className="kpi-value">{model.base_rate !== null ? `${(model.base_rate * 100).toFixed(0)}%` : "—"}</div>
                  <div className="kpi-note">share of clusters that beat SPY by 5pp+</div>
                </div>
                <div className="kpi-tile">
                  <div className="kpi-label">Held-out test accuracy</div>
                  <div className="kpi-value">{model.held_out_test_accuracy !== null ? `${(model.held_out_test_accuracy * 100).toFixed(0)}%` : "—"}</div>
                  <div className="kpi-note">n={model.test_size} test split</div>
                </div>
                <div className="kpi-tile">
                  <div className="kpi-label">Held-out test AUC</div>
                  <div className="kpi-value">{model.held_out_test_auc !== null ? model.held_out_test_auc.toFixed(3) : "—"}</div>
                  <div className="kpi-note">0.50 = coin flip</div>
                </div>
              </div>
              <p className="mut" style={{ fontSize: 11.5, marginTop: 12 }}>{model.note}</p>
              <p className="mut" style={{ fontSize: 11.5, marginTop: 8, color: "var(--accent-2)" }}>
                Honest read: test AUC near 0.50 means this specific 4-feature model does not
                reliably separate winners from losers out-of-sample on this sample size — the
                coefficients are shown for interpretability and as a template, not as a working
                predictive signal. See README Limitations.
              </p>
            </>
          ) : (
            <p className="event-summary">{model?.note ?? "Loading…"}</p>
          )}
        </div>
      </div>

      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-head"><h2>4. Data provenance</h2></div>
        <div className="card-body event-summary">
          {meta ? (
            <>
              <p>
                Quarters: <span className="num">{meta.quarters.join(", ")}</span> ·{" "}
                {meta.total_purchase_rows.toLocaleString()} raw open-market purchase rows →{" "}
                {meta.total_clusters_detected.toLocaleString()} clusters detected →{" "}
                {meta.clusters_with_price_data.toLocaleString()} with usable forward price data
                ({meta.clusters_dropped_no_price_data.toLocaleString()} dropped, mostly delisted/thinly-traded tickers with no yfinance history).
              </p>
              <p className="mut" style={{ fontSize: 11.5, marginTop: 8 }}>
                Generated {meta.generated_utc} · Sources: {meta.sources.join("; ")}
              </p>
            </>
          ) : (
            "Loading…"
          )}
        </div>
      </div>
    </div>
  );
}
