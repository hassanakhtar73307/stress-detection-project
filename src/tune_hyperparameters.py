"""
tune_hyperparameters.py
Performs grid search for Random Forest and XGBoost on a held-out
validation split (not nested in LOSO, per the proposal's accepted
fallback for time-constrained projects). Outputs best hyperparameters
to be used in the final LOSO evaluation and final model training.
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
import json

df = pd.read_csv("data/processed/features_traditional.csv")
feature_cols = [c for c in df.columns if c not in ("subject", "label")]
X = df[feature_cols].values
y = df["label"].values
groups = df["subject"].values

# Held-out validation split by SUBJECT (not by row) to avoid leakage
splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
train_idx, val_idx = next(splitter.split(X, y, groups))
X_train, X_val = X[train_idx], X[val_idx]
y_train, y_val = y[train_idx], y[val_idx]
print(f"Train: {len(X_train)} windows, Val: {len(X_val)} windows")

# --- Random Forest grid search ---
print("\nGrid searching Random Forest...")
rf_grid = {
    "n_estimators": [100, 300, 500],
    "max_depth": [5, 10, 15, 20],
}
rf_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    rf_grid, cv=3, scoring="f1_macro", n_jobs=-1
)
rf_search.fit(X_train, y_train)
print(f"Best RF params: {rf_search.best_params_}")
print(f"Best RF CV F1-macro: {rf_search.best_score_:.3f}")
val_score_rf = rf_search.score(X_val, y_val)
print(f"RF held-out validation F1-macro: {val_score_rf:.3f}")

# --- XGBoost grid search ---
print("\nGrid searching XGBoost...")
y_train_xgb = y_train - 1
y_val_xgb = y_val - 1
xgb_grid = {
    "learning_rate": [0.01, 0.1, 0.3],
    "max_depth": [3, 6, 10],
}
xgb_search = GridSearchCV(
    XGBClassifier(n_estimators=300, eval_metric="mlogloss", random_state=42),
    xgb_grid, cv=3, scoring="f1_macro", n_jobs=-1
)
xgb_search.fit(X_train, y_train_xgb)
print(f"Best XGB params: {xgb_search.best_params_}")
print(f"Best XGB CV F1-macro: {xgb_search.best_score_:.3f}")
val_score_xgb = xgb_search.score(X_val, y_val_xgb)
print(f"XGB held-out validation F1-macro: {val_score_xgb:.3f}")

# Save results
results = {
    "random_forest": {"best_params": rf_search.best_params_, "cv_f1_macro": rf_search.best_score_, "val_f1_macro": val_score_rf},
    "xgboost": {"best_params": xgb_search.best_params_, "cv_f1_macro": xgb_search.best_score_, "val_f1_macro": val_score_xgb},
}
with open("models/hyperparameter_search_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved models/hyperparameter_search_results.json")