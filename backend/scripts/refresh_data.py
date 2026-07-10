"""
refresh_data.py
-----------------
Paper Trail's end-to-end build pipeline. Reads the filtered SEC Form 4
purchase rows produced by `fetch_sec_data.py`, detects insider **cluster-buy**
events, pulls forward stock prices (yfinance) for every ticker involved plus
SPY as a market benchmark, runs an event-study abnormal-return calculation,
engineers cluster-level features, fits a small interpretable logistic
regression, and writes the single committed dataset the FastAPI app actually
reads at runtime.

Run (from backend/, with venv active):
  python scripts/fetch_sec_data.py     # step 1: pull + filter raw SEC data (cached)
  python scripts/refresh_data.py       # step 2: cluster detect + price + event study + model

Outputs:
  backend/data/cache/prices/{TICKER}.csv ......... raw yfinance daily closes (gitignored)
  backend/data/cache/sector_info.json ............. yfinance sector lookups (gitignored)
  backend/data/processed/cluster_events.json ...... committed, app reads this at runtime

------------------------------------------------------------------------
Methodology summary (full writeup in README section 5)
------------------------------------------------------------------------
1. CLUSTER DETECTION -- greedy, non-overlapping 30-calendar-day windows.
   For each ticker, sort its open-market purchase (TRANS_CODE='P',
   TRANS_ACQUIRED_DISP_CD='A') rows by date. Anchor a window at the first
   unclustered transaction; pull in every later transaction for that ticker
   within 30 days of the anchor. If the window contains purchases from >= 2
   distinct insiders (by CIK), it's a cluster-buy event -- emit it and
   advance past every transaction it consumed (non-overlapping). Otherwise
   advance the anchor by one transaction and try again. This is a simple,
   auditable rule -- not a statistical clustering algorithm -- deliberately,
   so every event in the output can be traced back to the exact transactions
   that produced it.
2. MINIMUM CLUSTER SIZE FILTER -- clusters with combined purchase value under
   $1,000,000 are dropped. Sub-$1M clusters are dominated by routine small
   purchases (dividend reinvestment-adjacent buys, small 10%-owner top-ups)
   that add noise without adding signal; the academic cluster-buy literature
   (e.g. Cohen, Malloy & Pomorski 2012) similarly conditions on trade size.
3. EVENT STUDY -- for each surviving cluster, the "anchor" date is the date
   of the *last* qualifying transaction (the date the cluster condition was
   satisfied). Forward cumulative return for the ticker and for SPY is
   computed at +30/+60/+90 calendar days from the anchor (nearest available
   trading day). Abnormal return = ticker return - SPY return over the same
   window -- the standard, simplest form of an event-study "market-adjusted
   return" (no beta adjustment, disclosed as a limitation in the README).
4. LOGISTIC REGRESSION -- predicts whether a cluster "beats SPY by more than
   5% within 90 days" from four interpretable features: number of distinct
   insiders, log10(total purchase value), whether a CEO/CFO participated
   (vs. only directors/other officers/10%-owners), and sector. Coefficients
   and a held-out accuracy/AUC are written into the dataset and rendered on
   the Methodology page -- see README for why this is deliberately not a
   black box.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
FILTERED_DIR = BASE_DIR / "data" / "cache" / "sec_filtered"
PRICE_CACHE_DIR = BASE_DIR / "data" / "cache" / "prices"
SECTOR_CACHE_PATH = BASE_DIR / "data" / "cache" / "sector_info.json"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
OUT_PATH = PROCESSED_DIR / "cluster_events.json"

QUARTERS = ["2023q1", "2023q2", "2025q1"]
CLUSTER_WINDOW_DAYS = 30
MIN_CLUSTER_VALUE_USD = 1_000_000
FORWARD_WINDOWS = [30, 60, 90]
BEAT_MARGIN = 0.05  # "beats benchmark" means abnormal return > +5pp at 90d
BENCHMARK = "SPY"
CEO_CFO_TITLE_RE = r"CHIEF EXECUTIVE|^CEO|CEO\b|CHIEF FINANCIAL|^CFO|CFO\b|PRESIDENT"

warnings: List[str] = []


# ------------------------------------------------------------- 1. load SEC data
def load_sec_rows() -> pd.DataFrame:
    frames = []
    for q in QUARTERS:
        p = FILTERED_DIR / f"{q}.csv"
        if not p.exists():
            raise SystemExit(f"Missing {p} -- run scripts/fetch_sec_data.py first.")
        frames.append(pd.read_csv(p))
    df = pd.concat(frames, ignore_index=True)
    df["trans_date"] = pd.to_datetime(df["trans_date"], format="%d-%b-%Y", errors="coerce")
    df = df.dropna(subset=["trans_date"])
    df["ticker"] = df["ticker"].str.upper().str.strip()
    return df


# ------------------------------------------------------------- 2. cluster detection
def detect_clusters(df: pd.DataFrame) -> List[Dict[str, Any]]:
    clusters = []
    for ticker, g in df.groupby("ticker"):
        g = g.sort_values("trans_date")
        txns = g.to_dict("records")
        n = len(txns)
        i = 0
        while i < n:
            start = txns[i]["trans_date"]
            end = start + timedelta(days=CLUSTER_WINDOW_DAYS)
            j = i
            insiders = set()
            window = []
            while j < n and txns[j]["trans_date"] <= end:
                insiders.add(txns[j]["insider_cik"])
                window.append(txns[j])
                j += 1
            if len(insiders) >= 2:
                total_value = sum(t["value_usd"] for t in window)
                if total_value >= MIN_CLUSTER_VALUE_USD:
                    clusters.append(_build_cluster_record(ticker, window, insiders))
                i = j
            else:
                i += 1
    return clusters


def _build_cluster_record(ticker: str, window: List[Dict[str, Any]], insiders: set) -> Dict[str, Any]:
    issuer_name = pd.Series([t["issuer_name"] for t in window]).mode().iat[0]
    cluster_start = min(t["trans_date"] for t in window)
    cluster_end = max(t["trans_date"] for t in window)
    total_shares = sum(t["shares"] for t in window)
    total_value = sum(t["value_usd"] for t in window)

    # Aggregate to one row per distinct insider (some insiders -- typically
    # under automatic 10b5-1 purchase plans -- file dozens of small same-day
    # buys; a per-transaction table would be unreadable and inflate the
    # dataset for no analytical benefit). Each row sums shares/value across
    # every qualifying transaction that insider made inside this cluster
    # window and reports their first purchase date in it.
    by_insider: Dict[Any, Dict[str, Any]] = {}
    for t in window:
        cik = t["insider_cik"]
        title = t.get("title")
        title = "" if pd.isna(title) else str(title)
        if cik not in by_insider:
            by_insider[cik] = {
                "name": t["insider_name"],
                "relationship": t["relationship"],
                "title": title,
                "shares": 0.0,
                "value_usd": 0.0,
                "num_transactions": 0,
                "first_trans_date": t["trans_date"],
            }
        row = by_insider[cik]
        row["shares"] += float(t["shares"])
        row["value_usd"] += float(t["value_usd"])
        row["num_transactions"] += 1
        row["first_trans_date"] = min(row["first_trans_date"], t["trans_date"])

    insider_rows = []
    for row in sorted(by_insider.values(), key=lambda r: r["value_usd"], reverse=True):
        insider_rows.append({
            "name": row["name"],
            "relationship": row["relationship"],
            "title": row["title"],
            "shares": round(row["shares"], 2),
            "avg_price_per_share": round(row["value_usd"] / row["shares"], 4) if row["shares"] else 0.0,
            "value_usd": round(row["value_usd"], 2),
            "num_transactions": row["num_transactions"],
            "first_trans_date": row["first_trans_date"].strftime("%Y-%m-%d"),
        })

    relationships = " ".join(str(t["relationship"]) for t in window)
    titles_upper = " ".join(
        (str(t["title"]).upper() if not pd.isna(t.get("title")) else "") for t in window
    )
    has_officer = "Officer" in relationships
    has_ceo_cfo = bool(
        pd.Series([titles_upper]).str.contains(CEO_CFO_TITLE_RE, regex=True).iat[0]
    )

    return {
        "id": f"{ticker}_{cluster_end.strftime('%Y%m%d')}",
        "ticker": ticker,
        "issuer_name": issuer_name,
        "cluster_start": cluster_start.strftime("%Y-%m-%d"),
        "cluster_end": cluster_end.strftime("%Y-%m-%d"),
        "num_distinct_insiders": len(insiders),
        "num_transactions": len(window),
        "total_shares": total_shares,
        "total_value_usd": round(total_value, 2),
        "has_officer": has_officer,
        "has_ceo_cfo": has_ceo_cfo,
        "insiders": insider_rows,
    }


# ------------------------------------------------------------- 3. price fetch
def fetch_prices(tickers: List[str], start: str, end: str) -> Dict[str, pd.DataFrame]:
    PRICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    all_symbols = sorted(set(tickers) | {BENCHMARK})
    result: Dict[str, pd.DataFrame] = {}
    to_fetch = []
    for sym in all_symbols:
        cache_path = PRICE_CACHE_DIR / f"{sym}.csv"
        if cache_path.exists():
            cached = pd.read_csv(cache_path, parse_dates=["Date"]).set_index("Date")
            result[sym] = cached
        else:
            to_fetch.append(sym)

    print(f"[prices] {len(all_symbols) - len(to_fetch)} cached, {len(to_fetch)} to fetch from yfinance")
    batch = 60
    for k in range(0, len(to_fetch), batch):
        chunk = to_fetch[k:k + batch]
        try:
            data = yf.download(
                chunk, start=start, end=end, group_by="ticker",
                progress=False, threads=True, auto_adjust=True,
            )
        except Exception as exc:  # pragma: no cover
            warnings.append(f"yfinance batch download failed for {chunk[:3]}...: {exc}")
            continue
        for sym in chunk:
            try:
                if len(chunk) == 1:
                    sub = data[["Close"]].dropna()
                else:
                    sub = data[sym][["Close"]].dropna()
            except Exception:
                warnings.append(f"No price data returned for {sym}")
                continue
            if sub.empty:
                warnings.append(f"No price data returned for {sym}")
                continue
            sub.to_csv(PRICE_CACHE_DIR / f"{sym}.csv")
            result[sym] = sub
        print(f"[prices] fetched batch {k // batch + 1}/{(len(to_fetch) - 1) // batch + 1}")
    return result


# ------------------------------------------------------------- 4. event study
def _price_on_or_after(series: pd.DataFrame, target_date: pd.Timestamp, tolerance_days: int = 5) -> Optional[float]:
    window = series[(series.index >= target_date) & (series.index <= target_date + timedelta(days=tolerance_days))]
    if window.empty:
        return None
    return float(window.iloc[0]["Close"])


def _price_on_or_before(series: pd.DataFrame, target_date: pd.Timestamp, tolerance_days: int = 5) -> Optional[float]:
    window = series[(series.index <= target_date) & (series.index >= target_date - timedelta(days=tolerance_days))]
    if window.empty:
        return None
    return float(window.iloc[-1]["Close"])


def run_event_study(cluster: Dict[str, Any], prices: Dict[str, pd.DataFrame]) -> Optional[Dict[str, Any]]:
    ticker = cluster["ticker"]
    if ticker not in prices or BENCHMARK not in prices:
        return None
    tprices = prices[ticker]
    bprices = prices[BENCHMARK]

    anchor_date = pd.Timestamp(cluster["cluster_end"])
    anchor_price = _price_on_or_after(tprices, anchor_date) or _price_on_or_before(tprices, anchor_date)
    anchor_bench = _price_on_or_after(bprices, anchor_date) or _price_on_or_before(bprices, anchor_date)
    if anchor_price is None or anchor_bench is None:
        return None

    returns: Dict[str, Optional[float]] = {}
    for n in FORWARD_WINDOWS:
        target = anchor_date + timedelta(days=n)
        tp = _price_on_or_after(tprices, target) or _price_on_or_before(tprices, target, tolerance_days=8)
        bp = _price_on_or_after(bprices, target) or _price_on_or_before(bprices, target, tolerance_days=8)
        if tp is None or bp is None:
            returns[f"ticker_{n}d"] = None
            returns[f"spy_{n}d"] = None
            returns[f"abnormal_{n}d"] = None
            continue
        t_ret = tp / anchor_price - 1
        b_ret = bp / anchor_bench - 1
        returns[f"ticker_{n}d"] = round(t_ret, 4)
        returns[f"spy_{n}d"] = round(b_ret, 4)
        returns[f"abnormal_{n}d"] = round(t_ret - b_ret, 4)

    # daily cumulative-abnormal-return series for the drill-down chart
    car_series = []
    window_end = anchor_date + timedelta(days=max(FORWARD_WINDOWS) + 3)
    t_win = tprices[(tprices.index >= anchor_date - timedelta(days=2)) & (tprices.index <= window_end)]
    for dt, row in t_win.iterrows():
        bp = _price_on_or_before(bprices, dt, tolerance_days=5)
        if bp is None:
            continue
        t_ret = float(row["Close"]) / anchor_price - 1
        b_ret = bp / anchor_bench - 1
        car_series.append({
            "date": dt.strftime("%Y-%m-%d"),
            "ticker_return": round(t_ret, 4),
            "benchmark_return": round(b_ret, 4),
            "abnormal_return": round(t_ret - b_ret, 4),
        })

    return {
        "anchor_date": anchor_date.strftime("%Y-%m-%d"),
        "anchor_price": round(anchor_price, 4),
        "anchor_benchmark_price": round(anchor_bench, 4),
        "returns": returns,
        "beats_benchmark_90d": (returns.get("abnormal_90d") is not None and returns["abnormal_90d"] > BEAT_MARGIN),
        "car_series": car_series,
    }


# ------------------------------------------------------------- 5. sector lookup
def fetch_sectors(tickers: List[str]) -> Dict[str, Optional[str]]:
    cache: Dict[str, Optional[str]] = {}
    if SECTOR_CACHE_PATH.exists():
        cache = json.loads(SECTOR_CACHE_PATH.read_text())
    missing = [t for t in tickers if t not in cache]
    print(f"[sectors] {len(tickers) - len(missing)} cached, {len(missing)} to fetch")
    for i, t in enumerate(missing):
        try:
            info = yf.Ticker(t).info
            cache[t] = info.get("sector") or None
        except Exception:
            cache[t] = None
        if (i + 1) % 25 == 0:
            SECTOR_CACHE_PATH.write_text(json.dumps(cache, indent=2))
            print(f"[sectors] {i + 1}/{len(missing)}")
    SECTOR_CACHE_PATH.write_text(json.dumps(cache, indent=2))
    return {t: cache.get(t) for t in tickers}


# ------------------------------------------------------------- 6. model
def train_model(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    for e in events:
        ab90 = e["returns"].get("abnormal_90d")
        if ab90 is None:
            continue
        rows.append({
            "num_distinct_insiders": e["num_distinct_insiders"],
            "log_total_value": np.log10(max(e["total_value_usd"], 1.0)),
            "has_ceo_cfo": int(e["has_ceo_cfo"]),
            "sector_tech": int(e.get("sector") in ("Technology",)),
            "sector_healthcare": int(e.get("sector") in ("Healthcare",)),
            "sector_financial": int(e.get("sector") in ("Financial Services",)),
            "label": int(e["beats_benchmark_90d"]),
        })
    dfm = pd.DataFrame(rows)
    feature_cols = [
        "num_distinct_insiders", "log_total_value", "has_ceo_cfo",
        "sector_tech", "sector_healthcare", "sector_financial",
    ]
    n = len(dfm)
    if n < 40:
        return {
            "trained": False,
            "n_samples": n,
            "note": "Too few labeled clusters with complete 90-day forward returns to fit a "
                    "meaningful logistic regression (need >=40). Coefficients omitted rather than "
                    "reported on an unreliable fit.",
        }

    X = dfm[feature_cols].values
    y = dfm["label"].values
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        Xs, y, test_size=0.25, random_state=42, stratify=y if len(set(y)) > 1 else None,
    )
    clf = LogisticRegression(max_iter=1000, C=1.0)
    clf.fit(X_train, y_train)
    train_acc = float(clf.score(X_train, y_train))
    test_acc = float(clf.score(X_test, y_test))
    try:
        test_auc = float(roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1]))
    except ValueError:
        test_auc = None

    # refit on all data for the coefficients we report/publish (small-N: use
    # the full sample for the reported model, held-out split only for the
    # honesty-check accuracy/AUC above)
    clf_full = LogisticRegression(max_iter=1000, C=1.0)
    clf_full.fit(Xs, y)

    return {
        "trained": True,
        "n_samples": n,
        "base_rate": round(float(y.mean()), 4),
        "features": feature_cols,
        "coefficients_standardized": {f: round(c, 4) for f, c in zip(feature_cols, clf_full.coef_[0])},
        "intercept": round(float(clf_full.intercept_[0]), 4),
        "held_out_test_accuracy": round(test_acc, 4),
        "held_out_train_accuracy": round(train_acc, 4),
        "held_out_test_auc": round(test_auc, 4) if test_auc is not None else None,
        "test_size": len(y_test),
        "note": "Logistic regression on standardized features, predicting whether a cluster beats "
                "SPY by more than 5 percentage points within 90 days. Coefficients are on "
                "standardized features so their signs/magnitudes are directly comparable to each "
                "other. Trained on all labeled events; the accuracy/AUC above come from a held-out "
                "25% test split (not the coefficients themselves) as an honesty check on a small "
                "sample -- see README Limitations for why this should be read as illustrative, "
                "not production-grade.",
    }


# ------------------------------------------------------------- main
def main() -> None:
    t0 = time.time()
    df = load_sec_rows()
    print(f"[load] {len(df):,} purchase rows across {df['ticker'].nunique():,} tickers")

    clusters = detect_clusters(df)
    print(f"[cluster] {len(clusters):,} clusters >= ${MIN_CLUSTER_VALUE_USD:,.0f} total value")

    tickers = sorted({c["ticker"] for c in clusters})
    min_start = min(pd.Timestamp(c["cluster_start"]) for c in clusters) - timedelta(days=10)
    max_end_target = max(pd.Timestamp(c["cluster_end"]) for c in clusters) + timedelta(days=max(FORWARD_WINDOWS) + 15)
    price_end = min(max_end_target, pd.Timestamp(datetime.now(timezone.utc).date()))

    prices = fetch_prices(tickers, min_start.strftime("%Y-%m-%d"), price_end.strftime("%Y-%m-%d"))

    events = []
    dropped_no_price = 0
    for c in clusters:
        study = run_event_study(c, prices)
        if study is None:
            dropped_no_price += 1
            continue
        c.update(study)
        events.append(c)
    print(f"[event-study] {len(events):,} clusters with usable price data "
          f"({dropped_no_price:,} dropped -- no/insufficient yfinance price history)")

    sectors = fetch_sectors(sorted({e["ticker"] for e in events}))
    for e in events:
        e["sector"] = sectors.get(e["ticker"])

    model = train_model(events)
    print(f"[model] trained={model.get('trained')} n_samples={model.get('n_samples')}")

    events.sort(key=lambda e: e["returns"].get("abnormal_90d") or -999, reverse=True)

    out = {
        "meta": {
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "quarters": QUARTERS,
            "sources": [
                "SEC DERA Insider Transactions Data Sets "
                "(https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets)",
                "yfinance (Yahoo Finance daily closes, auto-adjusted for splits/dividends)",
            ],
            "cluster_window_days": CLUSTER_WINDOW_DAYS,
            "min_cluster_value_usd": MIN_CLUSTER_VALUE_USD,
            "benchmark": BENCHMARK,
            "forward_windows_days": FORWARD_WINDOWS,
            "beat_margin": BEAT_MARGIN,
            "total_purchase_rows": int(len(df)),
            "total_clusters_detected": len(clusters),
            "clusters_with_price_data": len(events),
            "clusters_dropped_no_price_data": dropped_no_price,
            "distinct_tickers_with_events": len(tickers),
            "warnings": warnings,
        },
        "events": events,
        "model": model,
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"\n[done] wrote {OUT_PATH} ({size_kb:,.0f} KB) in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
