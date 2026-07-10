"""Loads the committed, precomputed dataset and exposes typed lookups.

The FastAPI app never talks to SEC EDGAR or yfinance on a live request --
all of that happens offline in `scripts/fetch_sec_data.py` and
`scripts/refresh_data.py`. This module just loads the resulting JSON once
and serves it in-memory.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "cluster_events.json"


@lru_cache(maxsize=1)
def load_dataset() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run scripts/fetch_sec_data.py then "
            f"scripts/refresh_data.py to build the dataset."
        )
    return json.loads(DATA_PATH.read_text())


def list_events() -> List[Dict[str, Any]]:
    return load_dataset()["events"]


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    for e in load_dataset()["events"]:
        if e["id"] == event_id:
            return e
    return None


def list_tickers() -> List[Dict[str, Any]]:
    events = load_dataset()["events"]
    by_ticker: Dict[str, Dict[str, Any]] = {}
    for e in events:
        t = e["ticker"]
        row = by_ticker.setdefault(t, {
            "ticker": t,
            "issuer_name": e["issuer_name"],
            "sector": e.get("sector"),
            "event_count": 0,
            "best_abnormal_90d": None,
            "latest_cluster_end": e["cluster_end"],
        })
        row["event_count"] += 1
        row["latest_cluster_end"] = max(row["latest_cluster_end"], e["cluster_end"])
        ab90 = e["returns"].get("abnormal_90d")
        if ab90 is not None and (row["best_abnormal_90d"] is None or ab90 > row["best_abnormal_90d"]):
            row["best_abnormal_90d"] = ab90
    return sorted(by_ticker.values(), key=lambda r: r["ticker"])


def events_for_ticker(ticker: str) -> List[Dict[str, Any]]:
    ticker = ticker.upper()
    return [e for e in load_dataset()["events"] if e["ticker"] == ticker]


def get_meta() -> Dict[str, Any]:
    return load_dataset()["meta"]


def get_model() -> Dict[str, Any]:
    return load_dataset()["model"]
