"""
Train a 3-class job fit classifier:
    GOOD_FIT (2) / MAYBE (1) / BAD_FIT (0)

Features (expanded from 4 to 10):
    emb_score, skill_score, exp_score, salary_log,
    title_similarity, keyword_overlap, skill_match_ratio,
    location_match, has_salary, description_length

Labels derived from gpt_score:
    >= 7.5 -> GOOD_FIT (2)
    >= 5.0 -> MAYBE (1)
    < 5.0  -> BAD_FIT (0)

Usage:
    python services/train_model.py

Saves to services/job_classifier_model.pkl
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report, confusion_matrix

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import APP_CONFIG
from services.ranker import init as init_ranker
from services.feature_extractor import extract_classification_features

CSV_PATH = str(APP_CONFIG["files"]["jobs_csv"])
MODEL_OUTPUT_PATH = str(Path(__file__).resolve().parent / "job_classifier_model.pkl")

# Label thresholds — adjusted to ensure all 3 classes have samples
GOOD_THRESHOLD = 7.0
MAYBE_THRESHOLD = 5.5


def score_to_label(score):
    if score >= GOOD_THRESHOLD:
        return 2  # GOOD_FIT
    elif score >= MAYBE_THRESHOLD:
        return 1  # MAYBE
    return 0  # BAD_FIT


def load_training_data():
    df = pd.read_csv(CSV_PATH)
    df = df[df["gpt_score"].notna()].copy()
    df["gpt_score"] = df["gpt_score"].astype(float)
    df = df[(df["gpt_score"] >= 0) & (df["gpt_score"] <= 10)]
    df["label"] = df["gpt_score"].apply(score_to_label)

    print(f"Loaded {len(df)} jobs")
    print(f"  GOOD_FIT (>={GOOD_THRESHOLD}): {(df['label'] == 2).sum()}")
    print(f"  MAYBE ({MAYBE_THRESHOLD}-{GOOD_THRESHOLD}):    {(df['label'] == 1).sum()}")
    print(f"  BAD_FIT (<{MAYBE_THRESHOLD}):     {(df['label'] == 0).sum()}")

    # Drop classes with too few samples
    class_counts = df['label'].value_counts()
    valid_classes = class_counts[class_counts >= 3].index
    df = df[df['label'].isin(valid_classes)].copy()

    if len(df['label'].unique()) < 2:
        print("ERROR: Need at least 2 classes with 3+ samples each.")
        sys.exit(1)

    return df


def build_feature_matrix(df):
    features = []
    valid_indices = []

    for idx, row in df.iterrows():
        job = {
            "job_title": row.get("title", ""),
            "company_name": row.get("company", ""),
            "job_description": row.get("job_description", ""),
            "experience_required": row.get("experience_required", ""),
            "salary": row.get("salary", ""),
            "location": row.get("location", ""),
            "created_at": row.get("created_at", ""),
        }
        try:
            feat = extract_classification_features(job)
            features.append(feat)
            valid_indices.append(idx)
        except Exception:
            continue

    return np.array(features), valid_indices


def train():
    init_ranker()

    df = load_training_data()
    if len(df) < 30:
        print("Not enough data (need 30+). Exiting.")
        return

    print("Extracting features...")
    X, valid_indices = build_feature_matrix(df)
    y = df.loc[valid_indices, "label"].values

    print(f"Feature matrix: {X.shape}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        min_samples_leaf=5,
        random_state=42,
    )

    cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="accuracy")
    print(f"\nCV Accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    print("\n===== TEST SET RESULTS =====")
    all_label_names = ["BAD_FIT", "MAYBE", "GOOD_FIT"]
    present_classes = sorted(np.unique(np.concatenate([y_test, preds])))
    label_names = [all_label_names[c] for c in present_classes]
    print(classification_report(y_test, preds, target_names=label_names, labels=present_classes))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, preds))

    # Feature importances
    feature_names = [
        "exp_score", "skill_score", "exp_skill_combo", "emb_score",
        "title_similarity", "keyword_overlap", "skill_match_ratio",
        "salary_log", "location_match", "desc_length_log",
    ]
    importances = model.feature_importances_
    print("\n===== FEATURE IMPORTANCES =====")
    for name, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1]):
        print(f"  {name:20s} {imp:.3f}")

    joblib.dump(model, MODEL_OUTPUT_PATH)
    print(f"\nModel saved to {MODEL_OUTPUT_PATH}")


if __name__ == "__main__":
    train()
