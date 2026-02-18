from operator import index
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

router = APIRouter()

# Globals set in startup (populated from backend/main.py)
MODELS = {}
REC_SCALED = None          # DataFrame with scaled features for existing customers
REC_CENTROIDS = None       # DataFrame of centroids
CLUSTER_PRODUCT_MEANS = None
CLUSTER_FEATURE_COLS = None
PRODUCT_COLS = None
RECOMMENDATIONS_CSV_PATH = None
RAW_DATA = None            # Original data with needed cols
REC_FEATURES = None
CLUSTER_INPUT_COLS = None

class ExistingCustomerRequest(BaseModel):
    customer_index: int = Field(..., ge=0, description="Index of existing customer")

@router.post("/recommend-existing")
def recommend_existing(payload: ExistingCustomerRequest):
    idx = payload.customer_index
    if idx not in RAW_DATA.index:
        raise HTTPException(status_code=404, detail="Customer index not found")

    feature_cols = [c for c in CLUSTER_FEATURE_COLS if c not in PRODUCT_COLS]
    customer_features = REC_SCALED.loc[[idx], feature_cols].values
    cluster = int(REC_SCALED.loc[idx, "Clusters"])
    centroid_features = REC_CENTROIDS.loc[cluster, feature_cols].values.reshape(1, -1)
    similarity = float(cosine_similarity(customer_features, centroid_features)[0][0])

    if similarity < 0.4:
        return {
            "customer_index": idx,
            "cluster": cluster,
            "similarity_score": similarity,
            "recommended_products": [],
            "message": "Similarity below threshold",
        }

    uplift = (CLUSTER_PRODUCT_MEANS.loc[cluster] - RAW_DATA.loc[idx, PRODUCT_COLS])
    uplift = uplift[uplift > 0].sort_values(ascending=False)
    top_products = list(uplift.head(3).index)

    return {
        "customer_index": idx,
        "cluster": cluster,
        "similarity_score": similarity,
        "recommended_products": top_products,
    }

@router.post("/recommend-new")
def recommend_new(payload: dict):
    incoming = pd.DataFrame([payload])
    # Validate columns
    missing = [c for c in CLUSTER_INPUT_COLS if c not in incoming.columns]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing features: {missing}")
    incoming = incoming[CLUSTER_INPUT_COLS]

    scaler = MODELS["scaler"]
    pca = MODELS["pca"]
    kmeans = MODELS["kmeans"]
    rec_scaler = MODELS["rec_scaler"]

    scaled_incoming = scaler.transform(incoming)
    pca_incoming = pca.transform(scaled_incoming)
    cluster = int(kmeans.predict(pca_incoming)[0])

    rec_row = incoming.copy()
    rec_row.insert(0, "Clusters", cluster)
    rec_row_scaled = rec_row.copy()
    rec_row_scaled[CLUSTER_INPUT_COLS] = rec_scaler.transform(rec_row_scaled[CLUSTER_INPUT_COLS])

    feature_cols = [c for c in CLUSTER_INPUT_COLS if c not in PRODUCT_COLS]
    centroid_features = REC_CENTROIDS.loc[cluster, feature_cols].values.reshape(1, -1)
    similarity = float(cosine_similarity(rec_row_scaled[feature_cols], centroid_features)[0][0])

    if similarity < 0.4:
        return {
            "cluster": cluster,
            "similarity_score": similarity,
            "recommended_products": [],
            "message": "Similarity below threshold",
        }

    uplift = (CLUSTER_PRODUCT_MEANS.loc[cluster] - rec_row.loc[0, PRODUCT_COLS])
    uplift = uplift[uplift > 0].sort_values(ascending=False)
    top_products = list(uplift.head(3).index)

    return {
        "cluster": cluster,
        "similarity_score": similarity,
        "recommended_products": top_products,
    }



@router.get("/download-recommendations")
def download_recommendations():
    try:
        df = pd.read_csv(RECOMMENDATIONS_CSV_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recommendations file not found")
    return df.to_dict(orient="records")