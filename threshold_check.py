import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import precision_score, recall_score

model = xgb.XGBClassifier()
model.load_model("models/xgb_sentinel.ubj")

df = pd.read_csv("data/processed/acled_h3_gdelt_firms.csv", parse_dates=["event_date"], low_memory=False)
df = df.sort_values(["h3_id", "event_date"]).reset_index(drop=True)
for col, shift_n, new_col in [
    ("dangerous_count",  1, "dangerous_lag1"),
    ("dangerous_count",  2, "dangerous_lag2"),
    ("total_fatalities", 1, "fatalities_lag1"),
    ("battle_count",     1, "battle_lag1"),
    ("explosion_count",  1, "explosion_lag1"),
]:
    df[new_col] = df.groupby("h3_id")[col].shift(shift_n).fillna(0)
df = df.sort_values("event_date").reset_index(drop=True)

FEATURES = model.get_booster().feature_names

split_idx = int(len(df) * 0.9)
X_test = df[FEATURES].iloc[split_idx:].fillna(0)
y_test = df["label"].iloc[split_idx:]

proba = model.predict_proba(X_test)[:, 1]

n_days = max((df["event_date"].iloc[split_idx:].max() - df["event_date"].iloc[split_idx:].min()).days, 1)

print(f"{'Threshold':>10} {'Precision':>10} {'Recall':>10} {'Alerts/day':>12}")
print("-" * 46)
for t in [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
    pred = (proba >= t).astype(int)
    if pred.sum() == 0:
        print(f"{t:>10.2f} {'--':>10} {'--':>10} {'0':>12}")
        continue
    p = precision_score(y_test, pred)
    r = recall_score(y_test, pred)
    alerts_per_day = pred.sum() / n_days
    print(f"{t:>10.2f} {p:>10.3f} {r:>10.3f} {alerts_per_day:>12.1f}")
