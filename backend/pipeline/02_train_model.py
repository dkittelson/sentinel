"""
Step 2: XGBoost Model Training
Trains a binary classifier to predict escalation in the next week for a given H3 hex.
Auto-detects the richest available feature file (ACLED+GDELT+FIRMS > ACLED+GDELT > ACLED only).
Output: models/xgb_sentinel.ubj  (model)  +  models/eval_report.txt
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import (
    classification_report, roc_auc_score,
    precision_recall_curve, average_precision_score
)
import matplotlib.pyplot as plt
import os

# ── Config ────────────────────────────────────────────────────────────────────
# Use richest available data file (add GDELT/FIRMS/weather as they become available)
for candidate in [
    "data/processed/acled_h3_gdelt_firms_weather.csv",
    "data/processed/acled_h3_gdelt_firms.csv",
    "data/processed/acled_h3_gdelt.csv",
    "data/processed/acled_h3.csv",
]:
    if os.path.exists(candidate):
        PROCESSED_PATH = candidate
        break

MODEL_OUT  = "models/xgb_sentinel.ubj"
REPORT_OUT = "models/eval_report.txt"
PLOT_OUT   = "models/feature_importance.png"

# Base features always present
BASE_FEATURES = [
    "event_count",
    "total_fatalities",
    "max_fatalities",
    "battle_count",
    "explosion_count",
    "vac_count",
    "population_best",
    "unique_actors",
    "event_count_roll2w",
    "fatalities_roll2w",
    "event_count_roll4w",
    "fatalities_roll4w",
    # Velocity / momentum
    "event_count_delta",
    "fatality_delta",
    "event_velocity",
    "fatality_velocity",
    # Spatial lag
    "neighbor_event_avg",
    "neighbor_fatal_sum",
    # Actor novelty
    "actor_pair_count",
    "actor_pair_delta",
    "actor_pair_velocity",
]

# GDELT features (available after 03_ingest_gdelt.py)
GDELT_FEATURES = [
    "gdelt_event_count",
    "gdelt_avg_tone",
    "gdelt_min_goldstein",
    "gdelt_avg_goldstein",
    "gdelt_num_articles",
    "gdelt_hostility",
    "neighbor_gdelt_hostility_avg",  # spatial lag: ring-1 news hostility bleed
]

# FIRMS features (available after 04_ingest_firms.py)
FIRMS_FEATURES = [
    "firms_hotspot_count",
    "firms_avg_frp",
    "firms_max_frp",
    "firms_spike",
]

# Weather features (available after 05_ingest_weather.py)
WEATHER_FEATURES = [
    "weather_temp_max",
    "weather_temp_mean",
    "weather_temp_anomaly",
    "weather_precip_sum",
    "weather_precip_anomaly",
    "weather_drought_days",
]

LABEL = "label_escalation"

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"Loading {PROCESSED_PATH}...")
df = pd.read_csv(PROCESSED_PATH, parse_dates=["week"])
df = df.sort_values("week").reset_index(drop=True)

print(f"  Rows: {len(df):,}  |  Hexes: {df['h3_id'].nunique():,}")
print(f"  Label balance: {df[LABEL].value_counts(normalize=True).round(3).to_dict()}")

# Dynamically include only features present in this file
FEATURES = BASE_FEATURES.copy()
for col in GDELT_FEATURES:
    if col in df.columns:
        FEATURES.append(col)
for col in FIRMS_FEATURES:
    if col in df.columns:
        FEATURES.append(col)
for col in WEATHER_FEATURES:
    if col in df.columns:
        FEATURES.append(col)

gdelt_active   = any(c in df.columns for c in GDELT_FEATURES)
firms_active   = any(c in df.columns for c in FIRMS_FEATURES)
weather_active = any(c in df.columns for c in WEATHER_FEATURES)
print(f"  Feature set: base"
      f"{' + GDELT' if gdelt_active else ''}"
      f"{' + FIRMS' if firms_active else ''}"
      f"{' + WEATHER' if weather_active else ''}"
      f" ({len(FEATURES)} features total)")

X = df[FEATURES].fillna(0)
y = df[LABEL]

# ── Imbalance weight ──────────────────────────────────────────────────────────
neg, pos = (y == 0).sum(), (y == 1).sum()
scale_pos_weight = neg / pos
print(f"\n  scale_pos_weight = {scale_pos_weight:.2f}  ({neg} neg / {pos} pos)")

# ── Time-Series Cross Validation ──────────────────────────────────────────────
# Use TimeSeriesSplit to respect temporal ordering — never train on future data.
tscv = TimeSeriesSplit(n_splits=5)

print("\nRunning 5-fold time-series cross-validation...")

fold_aucs, fold_aps = [], []

for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        early_stopping_rounds=30,
        random_state=42,
        verbosity=0,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    proba = model.predict_proba(X_val)[:, 1]
    auc = roc_auc_score(y_val, proba)
    ap  = average_precision_score(y_val, proba)
    fold_aucs.append(auc)
    fold_aps.append(ap)
    print(f"  Fold {fold+1}: ROC-AUC = {auc:.3f}  |  Avg Precision = {ap:.3f}")

print(f"\n  Mean ROC-AUC:        {np.mean(fold_aucs):.3f} ± {np.std(fold_aucs):.3f}")
print(f"  Mean Avg Precision:  {np.mean(fold_aps):.3f} ± {np.std(fold_aps):.3f}")

# ── Final Model: Train on All Data ────────────────────────────────────────────
print("\nTraining final model on full dataset...")

# Hold out last 10% for final evaluation report
split_idx = int(len(X) * 0.9)
X_train_f, X_test_f = X.iloc[:split_idx], X.iloc[split_idx:]
y_train_f, y_test_f = y.iloc[:split_idx], y.iloc[split_idx:]

final_model = xgb.XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    eval_metric="aucpr",
    early_stopping_rounds=30,
    random_state=42,
    verbosity=0,
)
final_model.fit(
    X_train_f, y_train_f,
    eval_set=[(X_test_f, y_test_f)],
    verbose=False,
)

# ── Evaluate ──────────────────────────────────────────────────────────────────
proba_test = final_model.predict_proba(X_test_f)[:, 1]
pred_test  = (proba_test >= 0.4).astype(int)  # threshold tuned for recall

roc_auc = roc_auc_score(y_test_f, proba_test)
avg_prec = average_precision_score(y_test_f, proba_test)
report   = classification_report(y_test_f, pred_test, target_names=["No Escalation", "Escalation"])

print(f"\nFinal Model — Held-out Test Set (last 10% by time):")
print(f"  ROC-AUC:       {roc_auc:.3f}")
print(f"  Avg Precision: {avg_prec:.3f}")
print(f"\n{report}")

# ── Save Model ────────────────────────────────────────────────────────────────
os.makedirs("models", exist_ok=True)
final_model.save_model(MODEL_OUT)
print(f"Model saved → {MODEL_OUT}")

# ── Save Eval Report ──────────────────────────────────────────────────────────
with open(REPORT_OUT, "w") as f:
    f.write(f"Sentinel XGBoost — Evaluation Report\n")
    f.write(f"{'='*50}\n\n")
    f.write(f"CV Mean ROC-AUC:       {np.mean(fold_aucs):.3f} ± {np.std(fold_aucs):.3f}\n")
    f.write(f"CV Mean Avg Precision: {np.mean(fold_aps):.3f} ± {np.std(fold_aps):.3f}\n\n")
    f.write(f"Final Test ROC-AUC:       {roc_auc:.3f}\n")
    f.write(f"Final Test Avg Precision: {avg_prec:.3f}\n\n")
    f.write(report)
print(f"Eval report saved → {REPORT_OUT}")

# ── Feature Importance Plot ───────────────────────────────────────────────────
importance = pd.Series(
    final_model.feature_importances_,
    index=FEATURES
).sort_values(ascending=True)

fig, ax = plt.subplots(figsize=(8, 5))
importance.plot(kind="barh", ax=ax, color="#e05c5c")
ax.set_title("Feature Importance — Sentinel XGBoost")
ax.set_xlabel("Gain")
plt.tight_layout()
plt.savefig(PLOT_OUT, dpi=150)
print(f"Feature importance plot saved → {PLOT_OUT}")
