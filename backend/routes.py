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

# Similarity threshold — lowered to 0.1 so more customers get recommendations.
# Cosine similarity on a 16-dim scaled space is often low (0.05-0.7 is typical).
SIMILARITY_THRESHOLD = 0.4


class ExistingCustomerRequest(BaseModel):
    customer_index: int = Field(..., ge=0, description="Index of existing customer")


def _interpret_similarity(score: float) -> str:
    """Human-readable label for the similarity score."""
    if score >= 0.7:
        return "Very High"
    elif score >= 0.5:
        return "High"
    elif score >= 0.3:
        return "Moderate"
    elif score >= 0.1:
        return "Low"
    else:
        return "Very Low"


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

    # Always compute uplift — even for low similarity, show best products
    uplift = (CLUSTER_PRODUCT_MEANS.loc[cluster] - RAW_DATA.loc[idx, PRODUCT_COLS])
    uplift = uplift[uplift > 0].sort_values(ascending=False)
    top_products = list(uplift.head(3).index)

    response = {
        "customer_index": idx,
        "cluster": cluster,
        "similarity_score": round(similarity, 4),
        "similarity_level": _interpret_similarity(similarity),
        "recommended_products": top_products,
    }

    if similarity < SIMILARITY_THRESHOLD:
        response["warning"] = (
            "Very low similarity to cluster centroid. "
            "This customer may be an outlier or the model may need retraining."
        )

    return response


@router.post("/recommend-new")
def recommend_new(payload: dict):
    incoming = pd.DataFrame([payload])

    # --- Auto-derive dependent fields so users don't need to calculate them ---
    auto_derived = {}

    # Step 1: Derive Children = Kidhome + Teenhome (always — both fields are in the form)
    if "Kidhome" in incoming.columns and "Teenhome" in incoming.columns:
        kidhome = incoming["Kidhome"].fillna(0).iloc[0]
        teenhome = incoming["Teenhome"].fillna(0).iloc[0]
        auto_children = int(kidhome + teenhome)
        incoming["Children"] = auto_children
        auto_derived["Children"] = auto_children
    else:
        kidhome = 0
        teenhome = 0
        auto_children = 0
        incoming["Children"] = 0
        auto_derived["Children"] = 0

    # Step 2: Is_Parent = 1 if any children at home, else 0
    auto_is_parent = int(auto_children > 0)
    incoming["Is_Parent"] = auto_is_parent
    auto_derived["Is_Parent"] = auto_is_parent

    # Step 3: Family_Size = kids + teens + 1 self + 1 if living with partner
    living_with = incoming["Living_With"].fillna(1).iloc[0] if "Living_With" in incoming.columns else 1
    living_with = min(int(living_with), 2)   # clamp: 1=alone, 2=with partner
    extra_adults = 1 if living_with >= 2 else 0
    auto_family_size = int(kidhome + teenhome + 1 + extra_adults)
    incoming["Family_Size"] = auto_family_size
    auto_derived["Family_Size"] = auto_family_size

    # Step 4: Spent = sum of all product spend columns
    spend_cols = ["Wines", "Fruits", "Meat", "Fish", "Sweets", "Gold"]
    present_spend_cols = [c for c in spend_cols if c in incoming.columns]
    if present_spend_cols:
        auto_spent = float(incoming[present_spend_cols].fillna(0).sum(axis=1).iloc[0])
        incoming["Spent"] = auto_spent
        auto_derived["Spent"] = auto_spent

    # Validate columns after auto-derivation
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

    # Always compute uplift — give products regardless of similarity
    uplift = (CLUSTER_PRODUCT_MEANS.loc[cluster] - rec_row.loc[0, PRODUCT_COLS])
    uplift = uplift[uplift > 0].sort_values(ascending=False)
    top_products = list(uplift.head(3).index)

    # If no uplift products found (customer already spends more than cluster avg), return all products ranked
    if not top_products:
        top_products = list(CLUSTER_PRODUCT_MEANS.loc[cluster].sort_values(ascending=False).head(3).index)

    response = {
        "cluster": cluster,
        "similarity_score": round(similarity, 4),
        "similarity_level": _interpret_similarity(similarity),
        "recommended_products": top_products,
        "auto_derived_fields": auto_derived,  # shows what was auto-calculated
    }

    if similarity < SIMILARITY_THRESHOLD:
        response["warning"] = (
            "Very low similarity to cluster centroid. "
            "Check if your input values are realistic and consistent."
        )

    return response


@router.get("/download-recommendations")
def download_recommendations():
    try:
        df = pd.read_csv(RECOMMENDATIONS_CSV_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recommendations file not found")
    return df.to_dict(orient="records")