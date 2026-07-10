import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import type { ClusterEventDetail } from "../types";
import { fmtDate, fmtPct, fmtShares, fmtUsd } from "../format";
import StampBadge from "../components/StampBadge";
import InsiderList from "../components/InsiderList";
import CarChart from "../components/CarChart";

export default function EventDetail() {
  const { id = "" } = useParams();
  const [event, setEvent] = useState<ClusterEventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEvent(null);
    setError(null);
    api.event(id).then(setEvent).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return <div className="page"><div className="errbox">Failed to load event: {error}</div></div>;
  if (!event) return <div className="page"><div className="loading">Loading event…</div></div>;

  const r = event.returns;

  return (
    <div className="page">
      <div className="ticker-head">
        <div className="ticker-id">
          <span className="ticker-avatar">{event.ticker.slice(0, 4)}</span>
          <div className="ticker-name-block">
            <div className="tk">
              <Link to={`/tickers/${event.ticker}`}>{event.ticker}</Link>
            </div>
            <div className="nm">{event.issuer_name}{event.sector ? ` · ${event.sector}` : ""}</div>
          </div>
        </div>
        <StampBadge value={r.abnormal_90d} />
      </div>

      <p className="page-desc" style={{ marginBottom: 18 }}>
        {event.num_distinct_insiders} distinct insiders bought {event.ticker} on the open market
        between {fmtDate(event.cluster_start)} and {fmtDate(event.cluster_end)}
        {event.has_ceo_cfo ? ", including a CEO or CFO" : ", directors/10%-owners only"} —
        totaling {fmtUsd(event.total_value_usd)} across {fmtShares(event.total_shares)} shares.
        The event-study anchor date is {fmtDate(event.anchor_date)} (the date the cluster
        condition was met) at a reference price of ${event.anchor_price.toFixed(2)}.
      </p>

      <div className="kpi-row">
        <div className="kpi-tile">
          <div className="kpi-label">Abnormal return, 30d</div>
          <div className="kpi-value">{fmtPct(r.abnormal_30d)}</div>
          <div className="kpi-note">ticker {fmtPct(r.ticker_30d)} vs SPY {fmtPct(r.spy_30d)}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Abnormal return, 60d</div>
          <div className="kpi-value">{fmtPct(r.abnormal_60d)}</div>
          <div className="kpi-note">ticker {fmtPct(r.ticker_60d)} vs SPY {fmtPct(r.spy_60d)}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Abnormal return, 90d</div>
          <div className="kpi-value">{fmtPct(r.abnormal_90d)}</div>
          <div className="kpi-note">ticker {fmtPct(r.ticker_90d)} vs SPY {fmtPct(r.spy_90d)}</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Total purchased</div>
          <div className="kpi-value">{fmtUsd(event.total_value_usd)}</div>
          <div className="kpi-note">{event.num_transactions} qualifying transactions</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 18 }}>
        <div className="card">
          <div className="card-head">
            <h2>Cumulative return since cluster close</h2>
            <span className="hint">anchor {fmtDate(event.anchor_date)}</span>
          </div>
          <div className="card-body">
            <CarChart series={event.car_series} />
          </div>
        </div>
        <div className="card">
          <div className="card-head">
            <h2>Insiders in this cluster</h2>
            <span className="hint">{event.insiders.length} distinct</span>
          </div>
          <div className="card-body">
            <InsiderList insiders={event.insiders} />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h2>Case file</h2></div>
        <div className="card-body event-summary">
          Event ID <span className="num">{event.id}</span> · Cluster window {fmtDate(event.cluster_start)}
          {" "}– {fmtDate(event.cluster_end)} ({event.num_distinct_insiders} distinct insiders,{" "}
          {event.num_transactions} qualifying open-market purchase transactions, SEC transaction
          code &ldquo;P&rdquo; / acquired &ldquo;A&rdquo;). Benchmark: SPY, anchor price ${event.anchor_benchmark_price.toFixed(2)}.
          See the <Link to="/methodology">Methodology</Link> page for how clustering and abnormal
          returns are computed.
        </div>
      </div>
    </div>
  );
}
