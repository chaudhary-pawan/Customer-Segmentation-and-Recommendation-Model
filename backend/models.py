import joblib
import pandas as pd
from pathlib import Path
from typing import Dict, Any

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

MODEL_PATHS = {
    "scaler": MODELS_DIR / "scaler.pkl",
    "pca": MODELS_DIR / "pca.pkl",
    "kmeans": MODELS_DIR / "kmeans.pkl",
    "rec_scaler": MODELS_DIR / "rec_scaler.pkl",
    "rec_centroids": MODELS_DIR / "centroids.pkl",
    "cluster_product_means": MODELS_DIR / "cluster_product_means.pkl",
}

def load_models() -> Dict[str, Any]:
    models = {}
    for name, path in MODEL_PATHS.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing model file: {path}")
        models[name] = joblib.load(path)
    return models

def load_recommendations_csv(csv_path: Path) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing recommendations CSV at {csv_path}")
    return pd.read_csv(csv_path)