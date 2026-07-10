"""Per-ticker drill-down: cluster history for a single issuer."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ..models.schemas import ClusterEventDetail, TickerSummary
from ..services import data_loader

router = APIRouter(prefix="/api/tickers", tags=["tickers"])


@router.get("", response_model=List[TickerSummary])
def tickers():
    return data_loader.list_tickers()


@router.get("/{ticker}", response_model=List[ClusterEventDetail])
def ticker_events(ticker: str):
    events = data_loader.events_for_ticker(ticker)
    if not events:
        raise HTTPException(status_code=404, detail=f"No cluster-buy events found for '{ticker}'")
    return events
