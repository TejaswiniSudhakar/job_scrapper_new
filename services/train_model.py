import pandas as pd
import joblib
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor

from sklearn.metrics import (
    mean_absolute_error,
    r2_score
)

# ======================================
# LOAD DATA
# ======================================

df = pd.read_csv("jobs.csv")

# Remove rows without GPT score
df = df[df["gpt_score"].notna()]

# Fill nulls
for col in [
    "title",
    "job_description",
    "experience_required"
]:
    df[col] = df[col].fillna("")

# ======================================
# FEATURES
# ======================================

X = df[
    [
        "title",
        "job_description",
        "experience_required",
        "pre_score"
    ]
]

y = df["gpt_score"]

# ======================================
# SPLIT
# ======================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# ======================================
# PREPROCESSING
# ======================================

preprocessor = ColumnTransformer(
    [
        (
            "title",
            TfidfVectorizer(
                max_features=300
            ),
            "title"
        ),
        (
            "description",
            TfidfVectorizer(
                max_features=2000,
                stop_words="english"
            ),
            "job_description"
        ),
        (
            "experience",
            TfidfVectorizer(
                max_features=50
            ),
            "experience_required"
        )
    ],
    remainder="passthrough"
)

# ======================================
# MODEL
# ======================================

model = RandomForestRegressor(
    n_estimators=300,
    max_depth=20,
    random_state=42,
    n_jobs=-1
)

pipeline = Pipeline(
    [
        ("features", preprocessor),
        ("model", model)
    ]
)

# ======================================
# TRAIN
# ======================================

pipeline.fit(
    X_train,
    y_train
)

# ======================================
# EVALUATE
# ======================================

preds = pipeline.predict(X_test)

mae = mean_absolute_error(
    y_test,
    preds
)

r2 = r2_score(
    y_test,
    preds
)

rounded_preds = np.round(preds)

accuracy = (
    rounded_preds == y_test
).mean()

within_one = (
    np.abs(
        rounded_preds - y_test
    ) <= 1
).mean()

print("\n===== RESULTS =====")

print(
    "MAE:",
    round(mae, 3)
)

print(
    "R2 :",
    round(r2, 3)
)

print(
    "Exact Accuracy:",
    round(
        accuracy * 100,
        2
    ),
    "%"
)

print(
    "Within ±1:",
    round(
        within_one * 100,
        2
    ),
    "%"
)

# ======================================
# SAVE MODEL
# ======================================

joblib.dump(
    pipeline,
    "job_rank_model.pkl"
)

print("Model saved.")