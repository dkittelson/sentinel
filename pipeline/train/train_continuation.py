import pandas as pd
import numpy as np
import os
import xgboost as xgb

def train_continuation():
    if os.path.exists("models/xgb_continuation.ubj"):
        print("Cache hit")
        return
    
    # Load data and define features
    df = pd.read_parquet("data/processed/continuation_set.parquet")
    FEATURES = [
        "event_count_x", "fatality_best", "is_state_based", "is_non_state", "is_one_sided",
        "dangerous_roll14d", "ntl_mean", "siren_count",
        "is_ramadan", "is_jerusalem_day", "is_election_window"
    ]

    X = df[FEATURES]
    y = df["label"]

    # Temporal train/test split
    train = df[df["date"] < pd.Timestamp("2024-07-01").date()]
    test = df[df["date"] >= pd.Timestamp("2024-07-01").date()]

    X_train, y_train = train[FEATURES], train["label"]
    X_test, y_test = test[FEATURES], test["label"]  


    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        eval_metric="aucpr",
        random_state=42
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    # Save model
    os.makedirs("models", exist_ok=True)
    model.save_model("models/xgb_continuation.ubj")
    print("Onset model saved to models/xgb_continuation.ubj")

if __name__ == "__main__":
    train_continuation()





    

