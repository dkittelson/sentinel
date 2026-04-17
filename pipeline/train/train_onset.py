import pandas as pd
import numpy as np
import os
import xgboost as xgb

def train_onset():
    if os.path.exists("models/xgb_onset.ubj"):
        print("Cache hit")
        return
    
    # Load data and define features
    df = pd.read_parquet("data/processed/onset_set.parquet")
    FEATURES = [
        "ntl_mean", "goldstein_mean", "tone_mean", "mentions_sum",
        "siren_count", "population", "hospital_count", "school_count",
        "is_ramadan", "is_jerusalem_day", "is_election_window"
    ]

    X = df[FEATURES]
    y = df["label"]

    # Temporal train/test split
    train = df[df["date"] < pd.Timestamp("2024-07-01").date()]
    test = df[df["date"] >= pd.Timestamp("2024-07-01").date()]

    X_train, y_train = train[FEATURES], train["label"]
    X_test, y_test = test[FEATURES], test["label"]  

    # Compute scale_pos_weight and train
    scale = (y_train == 0).sum() / (y_train == 1).sum()

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=scale,
        eval_metric="aucpr",
        random_state=42
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    # Save model
    os.makedirs("models", exist_ok=True)
    model.save_model("models/xgb_onset.ubj")
    print("Onset model saved to models/xgb_onset.ubj")

if __name__ == "__main__":
    train_onset()





    

