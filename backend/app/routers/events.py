"""Cluster-buy event endpoints: leaderboard + per-event drill-down."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.schemas import ClusterEventDetail, ClusterEventSummary
from ..services import data_loader

router = APIRouter(prefix="/api/events", tags=["events"])


def _to_summary(e: dict) -> dict:
    return {k: v for k, v in e.items() if k not in ("insiders", "car_series", "anchor_benchmark_price")}


@router.get("", response_model=List[ClusterEventSummary])
def leaderboard(
    sort: str = Query("abnormal_90d", description="abnormal_90d | total_value_usd | num_distinct_insiders | cluster_end"),
    order: str = Query("desc", description="asc | desc"),
    min_insiders: Optional[int] = Query(None),
    ceo_cfo_only: bool = Query(False),
    sector: Optional[str] = Query(None),
    limit: int = Query(500, le=1000),
):
    events = data_loader.list_events()

    if min_insiders is not None:
        events = [e for e in events if e["num_distinct_insiders"] >= min_insiders]
    if ceo_cfo_only:
        events = [e for e in events if e["has_ceo_cfo"]]
    if sector:
        events = [e for e in events if (e.get("sector") or "").lower() == sector.lower()]

    def key(e: dict):
        if sort == "abnormal_90d":
            v = e["returns"].get("abnormal_90d")
            return v if v is not None else -999
        if sort in ("total_value_usd", "num_distinct_insiders", "cluster_end"):
            return e[sort]
        return e["returns"].get("abnormal_90d") or -999

    events = sorted(events, key=key, reverse=(order == "desc"))
    return [_to_summary(e) for e in events[:limit]]


@router.get("/{event_id}", response_model=ClusterEventDetail)
def event_detail(event_id: str):
    e = data_loader.get_event(event_id)
    if e is None:
        raise HTTPException(status_code=404, detail=f"Event '{event_id}' not found")
    return e
