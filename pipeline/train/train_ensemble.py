"""Ensemble: XGBoost + LightGBM + LogisticRegression with isotonic calibration.

Trains three model variants for each task (onset, continuation),
averages their predictions, then calibrates with isotonic regression.
This mirrors the VIEWS (Uppsala) production architecture.
"""
import pandas as pd
import numpy as np
import os
import sys
import pickle
import xgboost as xgb
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score
from scipy.special import expit

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import TRAIN_CUTOFF, TEST_START, RANDOM_SEED
from train_onset import ONSET_FEATURES, focal_loss_objective, focal_eval_aucpr
from train_continuation import CONT_FEATURES

BASE = os.path.join(os.path.dirname(__file__), "..")
MODEL_DIR = os.path.join(BASE, "models")
ENSEMBLE_DIR = os.path.join(MODEL_DIR, "ensemble")


def _available(features, df):
    return [f for f in features if f in df.columns]


def _train_xgb_focal(X_train, y_train, X_val, y_val):
    """XGBoost with focal loss (best single model from prior experiments)."""
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    n_pos = max((y_train == 1).sum(), 1)
    params = {
        "max_depth": 5, "learning_rate": 0.05,
        "subsample": 0.7, "colsample_bytree": 0.7,
        "min_child_weight": 10, "seed": RANDOM_SEED,
        "disable_default_eval_metric": True,
    }
    model = xgb.train(
        params, dtrain, num_boost_round=500,
        obj=focal_loss_objective, custom_metric=focal_eval_aucpr,
        evals=[(dval, "val")], early_stopping_rounds=30, verbose_eval=0,
    )
    preds = expit(model.predict(dval))
    return model, preds, "xgb_focal"


def _train_lgbm(X_train, y_train, X_val, y_val):
    """LightGBM with class weighting."""
    n_pos = max((y_train == 1).sum(), 1)
    scale = (y_train == 0).sum() / n_pos
    model = lgb.LGBMClassifier(
        n_estimators=500, max_depth=5, learning_rate=0.05,
        scale_pos_weight=scale, subsample=0.7, colsample_bytree=0.7,
        min_child_samples=10, metric="average_precision",
        random_state=RANDOM_SEED, verbose=-1,
    )
    model.fit(X_train, y_train,
              eval_set=[(X_val, y_val)],
              callbacks=[lgb.early_stopping(30, verbose=False)])
    preds = model.predict_proba(X_val)[:, 1]
    return model, preds, "lgbm"


def _train_lr(X_train, y_train, X_val, y_val):
    """Logistic Regression with balanced class weights."""
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_train)
    X_va_s = scaler.transform(X_val)
    model = LogisticRegression(
        class_weight="balanced", C=1.0, max_iter=1000,
        random_state=RANDOM_SEED,
    )
    model.fit(X_tr_s, y_train)
    preds = model.predict_proba(X_va_s)[:, 1]
    return (model, scaler), preds, "lr"


def train_ensemble_model(name, df, feature_list):
    """Train 3-model ensemble + isotonic calibration for one task."""
    features = _available(feature_list, df)
    print(f"\n{'='*55}")
    print(f"  Ensemble: {name} ({len(features)} features)")
    print(f"{'='*55}")

    train_cutoff = pd.Timestamp(TRAIN_CUTOFF)
    test_start = pd.Timestamp(TEST_START)

    # Split: train | calibration (last 2 months of train) | test
    cal_start = train_cutoff - pd.Timedelta(days=60)
    train = df[df["date"] <= cal_start]
    cal = df[(df["date"] > cal_start) & (df["date"] <= train_cutoff)]
    test = df[df["date"] >= test_start]

    X_train = train[features].fillna(0)
    y_train = train["label"]
    X_cal = cal[features].fillna(0)
    y_cal = cal["label"]
    X_test = test[features].fillna(0)
    y_test = test["label"]

    print(f"  Train: {len(train):,} | Cal: {len(cal):,} | Test: {len(test):,}")
    print(f"  Pos rate: train={y_train.mean():.3f} cal={y_cal.mean():.3f} test={y_test.mean():.3f}")

    # Train all 3 models on train set, get cal predictions
    models = {}
    cal_preds_list = []
    test_preds_list = []

    for trainer in [_train_xgb_focal, _train_lgbm, _train_lr]:
        model, cal_p, model_name = trainer(X_train, y_train, X_cal, y_cal)
        models[model_name] = model

        # Get test predictions
        if model_name == "xgb_focal":
            test_p = expit(model.predict(xgb.DMatrix(X_test)))
        elif model_name == "lr":
            lr_model, scaler = model
            test_p = lr_model.predict_proba(scaler.transform(X_test))[:, 1]
        else:
            test_p = model.predict_proba(X_test)[:, 1]

        aucpr = average_precision_score(y_test, test_p)
        print(f"  {model_name:12s} test AUC-PR: {aucpr:.4f}")

        cal_preds_list.append(cal_p)
        test_preds_list.append(test_p)

    # Ensemble: simple average
    cal_ensemble = np.mean(cal_preds_list, axis=0)
    test_ensemble = np.mean(test_preds_list, axis=0)
    aucpr_ens = average_precision_score(y_test, test_ensemble)
    print(f"  {'ENSEMBLE':12s} test AUC-PR: {aucpr_ens:.4f}")

    # Isotonic calibration on cal set
    ir = IsotonicRegression(out_of_bounds="clip")
    ir.fit(cal_ensemble, y_cal)

    test_calibrated = ir.transform(test_ensemble)
    aucpr_cal = average_precision_score(y_test, test_calibrated)
    print(f"  {'CALIBRATED':12s} test AUC-PR: {aucpr_cal:.4f}")

    # Save
    os.makedirs(ENSEMBLE_DIR, exist_ok=True)
    artifacts = {
        "models": models,
        "features": features,
        "calibrator": ir,
    }
    save_path = os.path.join(ENSEMBLE_DIR, f"{name}_ensemble.pkl")
    with open(save_path, "wb") as f:
        pickle.dump(artifacts, f)
    print(f"  Saved: {save_path}")

    return aucpr_ens, aucpr_cal


def train_ensemble():
    onset_df = pd.read_parquet(os.path.join(BASE, "data", "processed", "onset_set.parquet"))
    cont_df = pd.read_parquet(os.path.join(BASE, "data", "processed", "continuation_set.parquet"))

    o_aucpr, o_cal = train_ensemble_model("onset", onset_df, ONSET_FEATURES)
    c_aucpr, c_cal = train_ensemble_model("continuation", cont_df, CONT_FEATURES)

    print(f"\n{'='*55}")
    print(f"  SUMMARY")
    print(f"{'='*55}")
    print(f"  Onset:        ensemble={o_aucpr:.4f}  calibrated={o_cal:.4f}")
    print(f"  Continuation: ensemble={c_aucpr:.4f}  calibrated={c_cal:.4f}")


if __name__ == "__main__":
    train_ensemble()
