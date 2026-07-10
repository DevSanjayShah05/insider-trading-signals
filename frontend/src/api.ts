// API client for the Paper Trail backend.
import type {
  ClusterEventDetail,
  ClusterEventSummary,
  HealthResponse,
  MetaResponse,
  ModelInfo,
  TickerSummary,
} from "./types";

export const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? "http://localhost:8010";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`);
  return res.json() as Promise<T>;
}

export interface LeaderboardParams {
  sort?: "abnormal_90d" | "total_value_usd" | "num_distinct_insiders" | "cluster_end";
  order?: "asc" | "desc";
  min_insiders?: number;
  ceo_cfo_only?: boolean;
  sector?: string;
  limit?: number;
}

function toQuery(params: object): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  }
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export const api = {
  events: (params: LeaderboardParams = {}) =>
    get<ClusterEventSummary[]>(`/api/events${toQuery(params)}`),
  event: (id: string) => get<ClusterEventDetail>(`/api/events/${id}`),
  tickers: () => get<TickerSummary[]>("/api/tickers"),
  tickerEvents: (ticker: string) => get<ClusterEventDetail[]>(`/api/tickers/${ticker}`),
  meta: () => get<MetaResponse>("/api/meta"),
  model: () => get<ModelInfo>("/api/model"),
  health: () => get<HealthResponse>("/api/health"),
};
