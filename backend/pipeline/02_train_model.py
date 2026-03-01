"""
Step 2: XGBoost Model Training
Trains a binary classifier to predict escalation in the next week for a given H3 hex.
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
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import os, json

# ── Config ────────────────────────────────────────────────────────────────────
PROCESSED_PATH = "data/processed/acled_h3.csv"
MODEL_OUT       = "models/xgb_sentinel.ubj"
REPORT_OUT      = "models/eval_report.txt"
PLOT_OUT        = "models/feature_importance.png"

FEATURES = [
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
]
LABEL = "label_escalation"

# ── Load ──────────────────────────────────────────────────────────────────────
print(f"Loading {PROCESSED_PATH}...")
df = pd.read_csv(PROCESSED_PATH, parse_dates=["week"])
df = df.sort_values("week").reset_index(drop=True)

print(f"  Rows: {len(df):,}  |  Hexes: {df['h3_id'].nunique():,}")
print(f"  Label balance: {df[LABEL].value_counts(normalize=True).round(3).to_dict()}")

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
