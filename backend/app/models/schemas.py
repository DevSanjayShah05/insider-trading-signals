"""Pydantic schemas for API responses."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class InsiderTransaction(BaseModel):
    name: str
    relationship: str
    title: str
    shares: float
    avg_price_per_share: float
    value_usd: float
    num_transactions: int
    first_trans_date: str


class ReturnsBlock(BaseModel):
    ticker_30d: Optional[float] = None
    spy_30d: Optional[float] = None
    abnormal_30d: Optional[float] = None
    ticker_60d: Optional[float] = None
    spy_60d: Optional[float] = None
    abnormal_60d: Optional[float] = None
    ticker_90d: Optional[float] = None
    spy_90d: Optional[float] = None
    abnormal_90d: Optional[float] = None


class CarPoint(BaseModel):
    date: str
    ticker_return: float
    benchmark_return: float
    abnormal_return: float


class ClusterEventSummary(BaseModel):
    id: str
    ticker: str
    issuer_name: str
    sector: Optional[str] = None
    cluster_start: str
    cluster_end: str
    num_distinct_insiders: int
    num_transactions: int
    total_shares: float
    total_value_usd: float
    has_officer: bool
    has_ceo_cfo: bool
    anchor_date: str
    anchor_price: float
    returns: ReturnsBlock
    beats_benchmark_90d: bool


class ClusterEventDetail(ClusterEventSummary):
    insiders: List[InsiderTransaction]
    anchor_benchmark_price: float
    car_series: List[CarPoint]


class TickerSummary(BaseModel):
    ticker: str
    issuer_name: str
    sector: Optional[str] = None
    event_count: int
    best_abnormal_90d: Optional[float] = None
    latest_cluster_end: str


class ModelInfo(BaseModel):
    trained: bool
    n_samples: int
    base_rate: Optional[float] = None
    features: Optional[List[str]] = None
    coefficients_standardized: Optional[Dict[str, float]] = None
    intercept: Optional[float] = None
    held_out_test_accuracy: Optional[float] = None
    held_out_train_accuracy: Optional[float] = None
    held_out_test_auc: Optional[float] = None
    test_size: Optional[int] = None
    note: str


class MetaResponse(BaseModel):
    generated_utc: str
    quarters: List[str]
    sources: List[str]
    cluster_window_days: int
    min_cluster_value_usd: float
    benchmark: str
    forward_windows_days: List[int]
    beat_margin: float
    total_purchase_rows: int
    total_clusters_detected: int
    clusters_with_price_data: int
    clusters_dropped_no_price_data: int
    distinct_tickers_with_events: int
    warnings: List[str]


class HealthResponse(BaseModel):
    status: str
    events: int
    tickers: int
    generated_utc: Optional[str] = None
