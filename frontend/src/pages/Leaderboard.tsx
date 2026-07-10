import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { ClusterEventSummary, MetaResponse } from "../types";
import { fmtDate, fmtPct, fmtUsd } from "../format";
import StampBadge from "../components/StampBadge";

type SortKey = "abnormal_90d" | "total_value_usd" | "num_distinct_insiders" | "cluster_end";

export default function Leaderboard() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<ClusterEventSummary[] | null>(null);
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("abnormal_90d");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [ceoCfoOnly, setCeoCfoOnly] = useState(false);
  const [minInsiders, setMinInsiders] = useState<number | undefined>(undefined);
  const [page, setPage] = useState(0);
  const pageSize = 30;

  useEffect(() => {
    setEvents(null);
    api
      .events({ sort, order, ceo_cfo_only: ceoCfoOnly, min_insiders: minInsiders })
      .then(setEvents)
      .catch((e) => setError(String(e)));
    setPage(0);
  }, [sort, order, ceoCfoOnly, minInsiders]);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
  }, []);

  const paged = useMemo(() => {
    if (!events) return [];
    return events.slice(page * pageSize, (page + 1) * pageSize);
  }, [events, page]);

  const avgAbnormal90 = useMemo(() => {
    if (!events || events.length === 0) return null;
    const vals = events.map((e) => e.returns.abnormal_90d).filter((v): v is number => v !== null);
    if (vals.length === 0) return null;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }, [events]);

  const beatRate = useMemo(() => {
    if (!events || events.length === 0) return null;
    const withData = events.filter((e) => e.returns.abnormal_90d !== null);
    if (withData.length === 0) return null;
    return withData.filter((e) => e.beats_benchmark_90d).length / withData.length;
  }, [events]);

  function toggleSort(key: SortKey) {
    if (sort === key) {
      setOrder(order === "desc" ? "asc" : "desc");
    } else {
      setSort(key);
      setOrder("desc");
    }
  }

  if (error) return <div className="page"><div className="errbox">Failed to load: {error}</div></div>;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Cluster-Buy Leaderboard</h1>
          <p className="page-desc">
            Every detected insider cluster-buy event — 2 or more distinct officers, directors, or
            10%-owners buying the same company's stock on the open market within a rolling 30-day
            window — ranked by abnormal return vs. SPY 90 days after the cluster closed.
          </p>
        </div>
      </div>

      <div className="kpi-row">
        <div className="kpi-tile">
          <div className="kpi-label">Cluster events</div>
          <div className="kpi-value">{meta?.clusters_with_price_data ?? "—"}</div>
          <div className="kpi-note">of {meta?.total_clusters_detected ?? "—"} detected</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Distinct tickers</div>
          <div className="kpi-value">{meta?.distinct_tickers_with_events ?? "—"}</div>
          <div className="kpi-note">across {meta?.quarters.length ?? "—"} quarters</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Avg abnormal return (90d)</div>
          <div className="kpi-value">{fmtPct(avgAbnormal90)}</div>
          <div className="kpi-note">vs. SPY, equal-weighted</div>
        </div>
        <div className="kpi-tile">
          <div className="kpi-label">Beat rate (90d, &gt;+5pp)</div>
          <div className="kpi-value">{beatRate !== null ? `${(beatRate * 100).toFixed(0)}%` : "—"}</div>
          <div className="kpi-note">of clusters with price data</div>
        </div>
      </div>

      <div className="filter-bar">
        <button
          className={`toggle-chip ${ceoCfoOnly ? "on" : ""}`}
          onClick={() => setCeoCfoOnly((v) => !v)}
          type="button"
        >
          CEO/CFO participated only
        </button>
        <select
          className="select-field"
          value={minInsiders ?? ""}
          onChange={(e) => setMinInsiders(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">Min. distinct insiders: any</option>
          <option value="2">2+</option>
          <option value="3">3+</option>
          <option value="4">4+</option>
          <option value="5">5+</option>
        </select>
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Ranked events</h2>
          <span className="hint">{events ? `${events.length} matching` : "loading…"}</span>
        </div>
        <div className="tbl-wrap">
          <table className="leaderboard">
            <thead>
              <tr>
                <th className="rank-cell">#</th>
                <th>Ticker</th>
                <th onClick={() => toggleSort("cluster_end")}>Cluster window</th>
                <th className="num" onClick={() => toggleSort("num_distinct_insiders")}>Insiders</th>
                <th className="num" onClick={() => toggleSort("total_value_usd")}>Total bought</th>
                <th>C-suite?</th>
                <th className="num">30d abn.</th>
                <th className="num">90d abn.</th>
                <th className="num" onClick={() => toggleSort("abnormal_90d")}>Result</th>
              </tr>
            </thead>
            <tbody>
              {events === null && (
                <tr><td colSpan={9} className="loading">Loading events…</td></tr>
              )}
              {events !== null && paged.length === 0 && (
                <tr><td colSpan={9} className="empty-state">No events match these filters.</td></tr>
              )}
              {paged.map((e, i) => (
                <tr key={e.id} onClick={() => navigate(`/events/${e.id}`)}>
                  <td className="rank-cell">{page * pageSize + i + 1}</td>
                  <td className="tk-cell">
                    {e.ticker}
                    <span className="nm">{e.issuer_name}</span>
                  </td>
                  <td className="mut" style={{ fontSize: 11.5 }}>
                    {fmtDate(e.cluster_start)} → {fmtDate(e.cluster_end)}
                  </td>
                  <td className="num">{e.num_distinct_insiders}</td>
                  <td className="num">{fmtUsd(e.total_value_usd)}</td>
                  <td>
                    {e.has_ceo_cfo ? <span className="cat-badge ceo">CEO/CFO</span> : <span className="mut">directors only</span>}
                  </td>
                  <td className="num">{fmtPct(e.returns.abnormal_30d)}</td>
                  <td className="num">{fmtPct(e.returns.abnormal_90d)}</td>
                  <td className="num"><StampBadge value={e.returns.abnormal_90d} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {events && events.length > pageSize && (
          <div className="pager" style={{ padding: "0 16px 14px" }}>
            <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>← Prev</button>
            <span className="mut">Page {page + 1} of {Math.ceil(events.length / pageSize)}</span>
            <button
              type="button"
              disabled={(page + 1) * pageSize >= events.length}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
