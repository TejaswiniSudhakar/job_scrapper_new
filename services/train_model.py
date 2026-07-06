"""
Train the job ranking model on the same numeric features that ranker.py
produces at inference time:

    [emb_score, skill_score, exp_score, salary_log]

Target: gpt_score (from the jobs.csv exported by the scraper pipeline).

Usage:
    python services/train_model.py

The trained model is saved to services/job_rank_model.pkl and loaded by
ranker.py at startup.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Ensure project root is on the path so we can import config/services
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import APP_CONFIG
from services.ranker import (
    init,
    extract_features,
)

# ======================================
# CONFIG
# ======================================
CSV_PATH = str(APP_CONFIG["files"]["jobs_csv"])
MODEL_OUTPUT_PATH = str(Path(__file__).resolve().parent / "job_rank_model.pkl")


# ======================================
# LOAD DATA
# ======================================
def load_training_data():
    df = pd.read_csv(CSV_PATH)

    # Need gpt_score as the training target
    df = df[df["gpt_score"].notna()].copy()
    df["gpt_score"] = df["gpt_score"].astype(float)

    # Filter out rows where gpt_score is clearly invalid
    df = df[(df["gpt_score"] >= 0) & (df["gpt_score"] <= 10)]

    print(f"Loaded {len(df)} jobs with valid gpt_score from {CSV_PATH}")
    return df


# ======================================
# EXTRACT FEATURES (same as ranker.py)
# ======================================
def build_feature_matrix(df):
    """Build the same [emb_score, skill_score, exp_score, salary_log] features
    that ranker.extract_features() produces at inference time."""
    features = []
    skipped = 0

    for _, row in df.iterrows():
        job = {
            "job_title": row.get("title", ""),
            "company_name": row.get("company", ""),
            "job_description": row.get("job_description", ""),
            "experience_required": row.get("experience_required", ""),
            "salary": row.get("salary", ""),
        }

        try:
            feat = extract_features(job)
            features.append(feat)
        except Exception as e:
            skipped += 1
            continue

    if skipped:
        print(f"Skipped {skipped} rows due to feature extraction errors")

    return np.array(features)


# ======================================
# TRAIN
# ======================================
def train():
    # Initialize the embedding model used by extract_features
    init()

    df = load_training_data()
    if len(df) < 20:
        print("Not enough training data (need at least 20 rows). Exiting.")
        return

    print("Extracting features (this may take a while)...")
    X = build_feature_matrix(df)

    # X may have fewer rows than df if some were skipped
    y = df["gpt_score"].values[: len(X)]

    if len(X) != len(y):
        # Align: only keep rows where features were successfully extracted
        y = y[: len(X)]

    print(f"Feature matrix shape: {X.shape}")
    print(f"Feature columns: [emb_score, skill_score, exp_score, salary_log]")

    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Model: GradientBoosting works well for small numeric feature sets
    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )

    # Cross-validation on training set
    cv_scores = cross_val_score(
        model, X_train, y_train, cv=5, scoring="neg_mean_absolute_error"
    )
    print(f"\nCross-validation MAE: {-cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

    # Final fit
    model.fit(X_train, y_train)

    # Evaluate on held-out test set
    preds = model.predict(X_test)
    preds = np.clip(preds, 0, 10)

    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    within_one = (np.abs(preds - y_test) <= 1).mean()
    within_half = (np.abs(preds - y_test) <= 0.5).mean()

    print("\n===== TEST SET RESULTS =====")
    print(f"MAE:          {mae:.3f}")
    print(f"R2:           {r2:.3f}")
    print(f"Within ±0.5:  {within_half * 100:.1f}%")
    print(f"Within ±1.0:  {within_one * 100:.1f}%")

    # Feature importances
    feature_names = ["emb_score", "skill_score", "exp_score", "salary_log"]
    importances = model.feature_importances_
    print("\n===== FEATURE IMPORTANCES =====")
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1]):
        print(f"  {name:15s} {imp:.3f}")

    # Save
    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f"\nModel saved to {MODEL_OUTPUT_PATH}")


if __name__ == "__main__":
    train()
