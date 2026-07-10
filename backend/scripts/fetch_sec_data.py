"""
fetch_sec_data.py
------------------
Downloads SEC DERA's quarterly "Insider Transactions" structured data sets
(bulk TSV extracts covering every Form 3/4/5 filed that quarter) and filters
them down to open-market insider *purchases* -- the raw material for Paper
Trail's cluster-buy detector.

Data source (no API key required):
  https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets
  ZIP URL pattern: https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{quarter}_form345.zip

Each quarterly ZIP contains several pipe/tab-separated tables. This script
only needs three of them:
  - SUBMISSION.tsv       one row per Form 3/4/5 filing (ticker, issuer, date)
  - REPORTINGOWNER.tsv   one row per insider named on a filing (name, title,
                          officer/director/10%-owner relationship flags)
  - NONDERIV_TRANS.tsv   one row per non-derivative (common stock) transaction
                          reported on a Form 4 (transaction code, shares,
                          price, acquired/disposed flag)

We filter NONDERIV_TRANS down to TRANS_CODE == 'P' (open-market purchase)
and TRANS_ACQUIRED_DISP_CD == 'A' (acquired, not disposed) -- SEC's own
transaction-code taxonomy for "this insider bought shares on the open
market with their own money," which is the standard definition used in the
academic insider-trading literature (Lakonishok & Lee 2001; Cohen, Malloy &
Pomorski 2012) as opposed to option exercises (code 'M'), gifts ('G'),
or plan-related transactions.

SEC requires a descriptive User-Agent on every request or it will 403/throttle
generic clients -- see USER_AGENT below.

Quarters pulled (see README for the full rationale):
  - 2023q1  Silicon Valley Bank / Signature Bank collapse (Mar 2023) --
            a period of acute, sector-concentrated volatility that is exactly
            the kind of environment where insider buying is most informative.
  - 2023q2  First Republic Bank collapse and the banking-crisis aftermath
            (Apr-Jun 2023) -- captures the tail of the same episode.
  - 2025q1  Most recent full quarter available in this sandbox at build time,
            covering the Feb-Mar 2025 tariff-driven equity selloff.

Outputs:
  backend/data/cache/sec_raw/{quarter}_form345.zip ......... raw ZIP (gitignored)
  backend/data/cache/sec_filtered/{quarter}.csv ............ filtered purchase
    rows, joined across SUBMISSION + REPORTINGOWNER + NONDERIV_TRANS
    (gitignored -- re-derivable by re-running this script)

Run:
  python backend/scripts/fetch_sec_data.py
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

USER_AGENT = "Paper Trail Portfolio Project research@example.com"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}

BASE_DIR = Path(__file__).resolve().parents[1]  # backend/
RAW_DIR = BASE_DIR / "data" / "cache" / "sec_raw"
FILTERED_DIR = BASE_DIR / "data" / "cache" / "sec_filtered"

ZIP_URL_TMPL = (
    "https://www.sec.gov/files/structureddata/data/"
    "insider-transactions-data-sets/{quarter}_form345.zip"
)

QUARTERS = ["2023q1", "2023q2", "2025q1"]


def download_quarter_zip(quarter: str) -> Path:
    dest = RAW_DIR / f"{quarter}_form345.zip"
    if dest.exists():
        print(f"[cache hit] {dest}")
        return dest
    url = ZIP_URL_TMPL.format(quarter=quarter)
    print(f"[download] {url}")
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    print(f"[saved] {dest} ({len(resp.content):,} bytes)")
    return dest


def _read_tsv_from_zip(zf: zipfile.ZipFile, name: str, usecols: list[str]) -> pd.DataFrame:
    with zf.open(name) as fh:
        return pd.read_csv(
            io.TextIOWrapper(fh, encoding="latin-1"),
            sep="\t",
            usecols=usecols,
            dtype=str,
            low_memory=False,
        )


def filter_quarter(quarter: str, zip_path: Path) -> pd.DataFrame:
    """Extract + join the three tables, filtered to open-market purchases."""
    with zipfile.ZipFile(zip_path) as zf:
        submission = _read_tsv_from_zip(
            zf,
            "SUBMISSION.tsv",
            ["ACCESSION_NUMBER", "FILING_DATE", "PERIOD_OF_REPORT", "ISSUERCIK",
             "ISSUERNAME", "ISSUERTRADINGSYMBOL", "DOCUMENT_TYPE"],
        )
        owners = _read_tsv_from_zip(
            zf,
            "REPORTINGOWNER.tsv",
            ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME",
             "RPTOWNER_RELATIONSHIP", "RPTOWNER_TITLE", "RPTOWNER_TXT"],
        )
        trans = _read_tsv_from_zip(
            zf,
            "NONDERIV_TRANS.tsv",
            ["ACCESSION_NUMBER", "TRANS_DATE", "TRANS_CODE",
             "TRANS_SHARES", "TRANS_PRICEPERSHARE", "TRANS_ACQUIRED_DISP_CD"],
        )

    # SEC's own taxonomy: 'P' = open-market or private purchase of
    # non-derivative security, acquired ('A') side of the transaction.
    trans = trans[(trans["TRANS_CODE"] == "P") & (trans["TRANS_ACQUIRED_DISP_CD"] == "A")].copy()
    trans["TRANS_SHARES"] = pd.to_numeric(trans["TRANS_SHARES"], errors="coerce")
    trans["TRANS_PRICEPERSHARE"] = pd.to_numeric(trans["TRANS_PRICEPERSHARE"], errors="coerce")
    trans = trans.dropna(subset=["TRANS_SHARES", "TRANS_PRICEPERSHARE"])
    trans = trans[(trans["TRANS_SHARES"] > 0) & (trans["TRANS_PRICEPERSHARE"] > 0)]

    merged = trans.merge(submission, on="ACCESSION_NUMBER", how="inner")
    # Restrict to actual Form 4s (DOCUMENT_TYPE '4' or '4/A'); drop rows with
    # no ticker symbol (some issuers, e.g. private funds, have none -- not
    # usable for the price-based event study downstream).
    merged = merged[merged["DOCUMENT_TYPE"].isin(["4", "4/A"])]
    merged = merged[merged["ISSUERTRADINGSYMBOL"].notna() & (merged["ISSUERTRADINGSYMBOL"].str.len() > 0)]

    merged = merged.merge(owners, on="ACCESSION_NUMBER", how="inner")

    merged["value_usd"] = merged["TRANS_SHARES"] * merged["TRANS_PRICEPERSHARE"]
    merged["quarter"] = quarter

    out = merged.rename(columns={
        "ACCESSION_NUMBER": "accession_number",
        "ISSUERTRADINGSYMBOL": "ticker",
        "ISSUERNAME": "issuer_name",
        "ISSUERCIK": "issuer_cik",
        "TRANS_DATE": "trans_date",
        "TRANS_SHARES": "shares",
        "TRANS_PRICEPERSHARE": "price_per_share",
        "RPTOWNERCIK": "insider_cik",
        "RPTOWNERNAME": "insider_name",
        "RPTOWNER_RELATIONSHIP": "relationship",
        "RPTOWNER_TITLE": "title",
    })[[
        "quarter", "accession_number", "ticker", "issuer_name", "issuer_cik",
        "trans_date", "insider_cik", "insider_name", "relationship", "title",
        "shares", "price_per_share", "value_usd",
    ]]

    return out


def main() -> None:
    FILTERED_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for q in QUARTERS:
        out_path = FILTERED_DIR / f"{q}.csv"
        if out_path.exists():
            print(f"[cache hit] {out_path}")
            frames.append(pd.read_csv(out_path))
            continue
        zip_path = download_quarter_zip(q)
        df = filter_quarter(q, zip_path)
        df.to_csv(out_path, index=False)
        print(f"[filtered] {q}: {len(df):,} open-market purchase rows -> {out_path}")
        frames.append(df)

    total = pd.concat(frames, ignore_index=True)
    print(f"\nTotal open-market purchase (code P / acquired A) rows across "
          f"{len(QUARTERS)} quarters: {len(total):,}")
    print(f"Distinct tickers: {total['ticker'].nunique():,}")
    print(f"Distinct insiders (CIK): {total['insider_cik'].nunique():,}")


if __name__ == "__main__":
    sys.exit(main())
