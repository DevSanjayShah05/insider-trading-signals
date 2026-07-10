// Shared types mirroring backend/app/models/schemas.py

export interface ReturnsBlock {
  ticker_30d: number | null;
  spy_30d: number | null;
  abnormal_30d: number | null;
  ticker_60d: number | null;
  spy_60d: number | null;
  abnormal_60d: number | null;
  ticker_90d: number | null;
  spy_90d: number | null;
  abnormal_90d: number | null;
}

export interface ClusterEventSummary {
  id: string;
  ticker: string;
  issuer_name: string;
  sector: string | null;
  cluster_start: string;
  cluster_end: string;
  num_distinct_insiders: number;
  num_transactions: number;
  total_shares: number;
  total_value_usd: number;
  has_officer: boolean;
  has_ceo_cfo: boolean;
  anchor_date: string;
  anchor_price: number;
  returns: ReturnsBlock;
  beats_benchmark_90d: boolean;
}

export interface InsiderTransaction {
  name: string;
  relationship: string;
  title: string;
  shares: number;
  avg_price_per_share: number;
  value_usd: number;
  num_transactions: number;
  first_trans_date: string;
}

export interface CarPoint {
  date: string;
  ticker_return: number;
  benchmark_return: number;
  abnormal_return: number;
}

export interface ClusterEventDetail extends ClusterEventSummary {
  insiders: InsiderTransaction[];
  anchor_benchmark_price: number;
  car_series: CarPoint[];
}

export interface TickerSummary {
  ticker: string;
  issuer_name: string;
  sector: string | null;
  event_count: number;
  best_abnormal_90d: number | null;
  latest_cluster_end: string;
}

export interface ModelInfo {
  trained: boolean;
  n_samples: number;
  base_rate: number | null;
  features: string[] | null;
  coefficients_standardized: Record<string, number> | null;
  intercept: number | null;
  held_out_test_accuracy: number | null;
  held_out_train_accuracy: number | null;
  held_out_test_auc: number | null;
  test_size: number | null;
  note: string;
}

export interface MetaResponse {
  generated_utc: string;
  quarters: string[];
  sources: string[];
  cluster_window_days: number;
  min_cluster_value_usd: number;
  benchmark: string;
  forward_windows_days: number[];
  beat_margin: number;
  total_purchase_rows: number;
  total_clusters_detected: number;
  clusters_with_price_data: number;
  clusters_dropped_no_price_data: number;
  distinct_tickers_with_events: number;
  warnings: string[];
}

export interface HealthResponse {
  status: string;
  events: number;
  tickers: number;
  generated_utc: string | null;
}
