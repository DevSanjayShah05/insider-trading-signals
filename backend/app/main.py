"""
Paper Trail -- Insider Cluster-Buy Signal Detector.

FastAPI service that serves precomputed insider cluster-buy events (SEC
Form 4 open-market purchases, clustered when >=2 distinct insiders buy the
same ticker within a rolling 30-day window) along with their event-study
forward returns vs. SPY and a small interpretable logistic regression.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models.schemas import HealthResponse, MetaResponse, ModelInfo
from .routers import events, tickers
from .services import data_loader

app = FastAPI(
    title="Paper Trail API",
    description="Insider cluster-buy signal detector, built on real SEC Form 4 filings and real forward stock returns.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickers.router)
app.include_router(events.router)


@app.get("/api/health", response_model=HealthResponse, tags=["meta"])
def health():
    ds = data_loader.load_dataset()
    return HealthResponse(
        status="ok",
        events=len(ds["events"]),
        tickers=len({e["ticker"] for e in ds["events"]}),
        generated_utc=ds["meta"].get("generated_utc"),
    )


@app.get("/api/meta", response_model=MetaResponse, tags=["meta"])
def meta():
    return data_loader.get_meta()


@app.get("/api/model", response_model=ModelInfo, tags=["meta"])
def model():
    return data_loader.get_model()
