from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path

from .models import load_models
from . import routes

app = FastAPI(title="Customer Segmentation & Recommendations", version="1.0.0")

# Mount frontend static files at root so assets load at their relative paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
app.mount("/", StaticFiles(directory=PROJECT_ROOT / "frontend", html=True), name="frontend")


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

    # Expected feature columns (authoritative)
    cluster_feature_cols = list(rec_scaler.feature_names_in_)
    cluster_input_cols = cluster_feature_cols.copy()
    product_cols = ["Wines", "Fruits", "Meat", "Fish", "Sweets", "Gold"]  # adjust if different
    rec_features = ["Clusters"] + cluster_feature_cols

    # Optional rename map: adjust if your CSV uses these alt names
    rename_map = {
        "MntWines": "Wines",
        "MntFruits": "Fruits",
        "MntMeatProducts": "Meat",
        "MntFishProducts": "Fish",
        "MntSweetProducts": "Sweets",
        "MntGoldProds": "Gold",
    }
    raw_data = raw_data.rename(columns=rename_map)

    # Validate required columns
    missing_cols = [c for c in rec_features if c not in raw_data.columns]
    if missing_cols:
        raise RuntimeError(f"CSV missing required columns: {missing_cols}")

    # Build DataFrame with only the needed cols, in the right order
    rec_scaled = raw_data[rec_features].copy()
    rec_scaled[cluster_feature_cols] = rec_scaler.transform(rec_scaled[cluster_feature_cols])

    # Bind globals for routes
    routes.RAW_DATA = raw_data.set_index(raw_data.index)
    routes.REC_SCALED = rec_scaled
    routes.REC_CENTROIDS = rec_centroids
    routes.CLUSTER_PRODUCT_MEANS = cluster_product_means
    routes.CLUSTER_FEATURE_COLS = cluster_feature_cols
    routes.PRODUCT_COLS = product_cols
    routes.REC_FEATURES = rec_features
    routes.CLUSTER_INPUT_COLS = cluster_input_cols

app.include_router(routes.router)

@app.get("/health")
def health():
    return {"status": "ok"}


# Root and static files are served by StaticFiles mounted at '/'
@app.get("/about")
def about():
    return {
        "app": "Customer Segmentation & Recommendations API",
        "version": "1.0.0",
        "description": "API for customer segmentation and product recommendations based on KMeans clustering."
    }

@app.get("/about")
def about():
    return {
        "app": "Customer Segmentation & Recommendations API",
        "version": "1.0.0",
        "description": "API for customer segmentation and product recommendations based on KMeans clustering."
    }