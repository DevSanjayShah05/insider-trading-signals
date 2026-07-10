import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import type { ClusterEventDetail } from "../types";
import { fmtDate, fmtPct, fmtUsd } from "../format";
import StampBadge from "../components/StampBadge";

export default function TickerDetail() {
  const { ticker = "" } = useParams();
  const [events, setEvents] = useState<ClusterEventDetail[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEvents(null);
    setError(null);
    api.tickerEvents(ticker).then(setEvents).catch((e) => setError(String(e)));
  }, [ticker]);

  if (error) return <div className="page"><div className="errbox">Failed to load: {error}</div></div>;
  if (!events) return <div className="page"><div className="loading">Loading ticker history…</div></div>;

  const first = events[0];

  return (
    <div className="page">
      <div className="ticker-head">
        <div className="ticker-id">
          <span className="ticker-avatar">{ticker.slice(0, 4)}</span>
          <div className="ticker-name-block">
            <div className="tk">{ticker}</div>
            <div className="nm">{first.issuer_name}{first.sector ? ` · ${first.sector}` : ""}</div>
          </div>
        </div>
        <span className="mut">{events.length} cluster-buy event{events.length !== 1 ? "s" : ""} on record</span>
      </div>

      <div className="card">
        <div className="card-head"><h2>Event history</h2></div>
        <div className="tbl-wrap">
          <table className="leaderboard">
            <thead>
              <tr>
                <th>Cluster window</th>
                <th className="num">Insiders</th>
                <th className="num">Total bought</th>
                <th>C-suite?</th>
                <th className="num">30d abn.</th>
                <th className="num">90d abn.</th>
                <th className="num">Result</th>
              </tr>
            </thead>
            <tbody>
              {events
                .slice()
                .sort((a, b) => (a.cluster_end < b.cluster_end ? 1 : -1))
                .map((e) => (
                  <tr key={e.id}>
                    <td>
                      <Link to={`/events/${e.id}`}>
                        {fmtDate(e.cluster_start)} → {fmtDate(e.cluster_end)}
                      </Link>
                    </td>
                    <td className="num">{e.num_distinct_insiders}</td>
                    <td className="num">{fmtUsd(e.total_value_usd)}</td>
                    <td>{e.has_ceo_cfo ? <span className="cat-badge ceo">CEO/CFO</span> : <span className="mut">directors only</span>}</td>
                    <td className="num">{fmtPct(e.returns.abnormal_30d)}</td>
                    <td className="num">{fmtPct(e.returns.abnormal_90d)}</td>
                    <td className="num"><StampBadge value={e.returns.abnormal_90d} /></td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
