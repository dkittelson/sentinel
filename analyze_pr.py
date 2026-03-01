"""
Precision-recall analysis: find if P>0.40 + R>0.80 is achievable,
and measure the impact of restricting to "active hexes" only.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
from scipy.special import expit
from sklearn.metrics import precision_score, recall_score, f1_score

# ── Load + lag + relabel (mirrors 02_train_model.py) ─────────────────────────
df = pd.read_csv("data/processed/acled_h3_gdelt_firms.csv",
                 parse_dates=["event_date"], low_memory=False)
df = df.sort_values(["h3_id", "event_date"]).reset_index(drop=True)

for col, shift_n, new_col in [
    ("dangerous_count",  1, "dangerous_lag1"),
    ("dangerous_count",  2, "dangerous_lag2"),
    ("total_fatalities", 1, "fatalities_lag1"),
    ("battle_count",     1, "battle_lag1"),
    ("explosion_count",  1, "explosion_lag1"),
]:
    df[new_col] = df.groupby("h3_id")[col].shift(shift_n).fillna(0)

df["_l1"] = df.groupby("h3_id")["dangerous_count"].shift(-1).fillna(0)
df["_l2"] = df.groupby("h3_id")["dangerous_count"].shift(-2).fillna(0)
df["_l3"] = df.groupby("h3_id")["dangerous_count"].shift(-3).fillna(0)
df["label"] = (df[["_l1", "_l2", "_l3"]].max(axis=1) > 0).astype(int)
df = df.drop(columns=["_l1", "_l2", "_l3"])
df["_rank_end"] = df.groupby("h3_id").cumcount(ascending=False)
df = df[df["_rank_end"] >= 3].drop(columns=["_rank_end"])
df = df.sort_values("event_date").reset_index(drop=True)

split_idx = int(len(df) * 0.9)
df_test = df.iloc[split_idx:].copy()
y_test  = df_test["label"].values

# ── Load models ───────────────────────────────────────────────────────────────
focal = xgb.Booster(); focal.load_model("models/xgb_focal.ubj")
std   = xgb.XGBClassifier(); std.load_model("models/xgb_standard.ubj")

cols   = focal.feature_names
X_test = df_test[cols].fillna(0)

fcl_prob = expit(focal.predict(xgb.DMatrix(X_test, feature_names=cols)))
std_prob = std.predict_proba(X_test)[:, 1]

n_days = max((df_test["event_date"].max() - df_test["event_date"].min()).days, 1)

# ── Full PR sweep (fine-grained) ──────────────────────────────────────────────
def sweep(proba, y_true, label, thresholds):
    print(f"\n{'─'*65}")
    print(f"  {label}")
    print(f"{'─'*65}")
    print(f"{'Thresh':>8} {'Prec':>8} {'Recall':>8} {'F1':>8} {'Alerts/day':>12}")
    print(f"{'─'*65}")
    best_f1 = -1
    for t in thresholds:
        pred = (proba >= t).astype(int)
        if pred.sum() == 0:
            continue
        p  = precision_score(y_true, pred, zero_division=0)
        r  = recall_score(y_true, pred, zero_division=0)
        f1 = f1_score(y_true, pred, zero_division=0)
        apd = pred.sum() / n_days
        star = " ◀ best F1" if f1 > best_f1 else ""
        if f1 > best_f1:
            best_f1 = f1
        # Only print rows with R >= 0.25 to keep it readable
        if r >= 0.25:
            print(f"{t:>8.2f} {p:>8.3f} {r:>8.3f} {f1:>8.3f} {apd:>12.1f}{star}")

thresholds = np.round(np.arange(0.05, 0.96, 0.01), 2)
sweep(fcl_prob, y_test, "FOCAL LOSS — full test set", thresholds)
sweep(std_prob, y_test, "STANDARD XGBoost — full test set", thresholds)

# ── Active hex filter ─────────────────────────────────────────────────────────
# "Active" = hex has recent signal: any dangerous event in 14d window,
#             yesterday, or a hot neighbor. Quiet hexes excluded from scoring.
df_test["active"] = (
    (df_test["dangerous_roll14d"] > 0) |
    (df_test["dangerous_lag1"]    > 0) |
    (df_test["neighbor_danger_avg"] > 0)
)
active = df_test["active"].values

print(f"\n{'='*65}")
print(f"  ACTIVE HEX FILTER SUMMARY")
print(f"{'='*65}")
print(f"  Active rows    : {active.sum():,} / {len(active):,}  ({active.mean()*100:.1f}%)")
print(f"  Label rate (active) : {y_test[active].mean()*100:.1f}%")
print(f"  Label rate (quiet)  : {y_test[~active].mean()*100:.2f}%")
print(f"  True positives in active hexes: {y_test[active].sum():,} / {y_test.sum():,} ({y_test[active].sum()/y_test.sum()*100:.1f}%)")

sweep(fcl_prob[active], y_test[active],
      "FOCAL LOSS — active hexes only", thresholds)
sweep(std_prob[active], y_test[active],
      "STANDARD XGBoost — active hexes only", thresholds)
