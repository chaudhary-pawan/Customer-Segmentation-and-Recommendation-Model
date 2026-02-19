from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path

from .models import load_models
from . import routes

app = FastAPI(title="Customer Segmentation & Recommendations", version="1.0.0")

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    models = load_models()
    routes.MODELS = models

    rec_centroids = models["rec_centroids"]
    cluster_product_means = models["cluster_product_means"]
    rec_scaler = models["rec_scaler"]

    project_root = Path(__file__).resolve().parents[1]
    data_path = project_root / "data" / "customer_recommendations.csv"
    raw_data_path = project_root / "data" / "customer_segmentation_data.csv"

    routes.RECOMMENDATIONS_CSV_PATH = data_path

    raw_data = pd.read_csv(raw_data_path)

    cluster_feature_cols = list(rec_scaler.feature_names_in_)
    cluster_input_cols = cluster_feature_cols.copy()
    product_cols = ["Wines", "Fruits", "Meat", "Fish", "Sweets", "Gold"]
    rec_features = ["Clusters"] + cluster_feature_cols

    rename_map = {
        "MntWines": "Wines",
        "MntFruits": "Fruits",
        "MntMeatProducts": "Meat",
        "MntFishProducts": "Fish",
        "MntSweetProducts": "Sweets",
        "MntGoldProds": "Gold",
    }
    raw_data = raw_data.rename(columns=rename_map)

    missing_cols = [c for c in rec_features if c not in raw_data.columns]
    if missing_cols:
        raise RuntimeError(f"CSV missing required columns: {missing_cols}")

    rec_scaled = raw_data[rec_features].copy()
    rec_scaled[cluster_feature_cols] = rec_scaler.transform(rec_scaled[cluster_feature_cols])

    routes.RAW_DATA = raw_data.set_index(raw_data.index)
    routes.REC_SCALED = rec_scaled
    routes.REC_CENTROIDS = rec_centroids
    routes.CLUSTER_PRODUCT_MEANS = cluster_product_means
    routes.CLUSTER_FEATURE_COLS = cluster_feature_cols
    routes.PRODUCT_COLS = product_cols
    routes.REC_FEATURES = rec_features
    routes.CLUSTER_INPUT_COLS = cluster_input_cols

# --- API routes under /api prefix to avoid any conflict with static files ---
app.include_router(routes.router, prefix="/api")

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/about")
def about():
    return {
        "app": "Customer Segmentation & Recommendations API",
        "version": "1.0.0",
    }

# --- Serve index.html at root ---
@app.get("/")
def serve_index():
    return FileResponse(PROJECT_ROOT / "frontend" / "index.html")

# --- Serve static frontend files (JS, CSS) at /static ---
app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "frontend"), name="frontend")