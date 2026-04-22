"""Bayesian hyperparameter tuning with Optuna + walk-forward CV."""
import pandas as pd
import numpy as np
import os
import sys
import xgboost as xgb
import optuna
from sklearn.metrics import average_precision_score
from scipy.special import expit

optuna.logging.set_verbosity(optuna.logging.WARNING)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import RANDOM_SEED
from train_onset import ONSET_FEATURES, focal_loss_objective, focal_eval_aucpr
from train_continuation import CONT_FEATURES

BASE = os.path.join(os.path.dirname(__file__), "..")

# Walk-forward folds for validation
CV_FOLDS = [
    {"train_end": "2023-06-30", "test_start": "2023-07-17", "test_end": "2023-09-30"},
    {"train_end": "2023-09-30", "test_start": "2023-10-17", "test_end": "2023-12-31"},
    {"train_end": "2023-12-31", "test_start": "2024-01-17", "test_end": "2024-03-31"},
    {"train_end": "2024-03-31", "test_start": "2024-04-17", "test_end": "2024-06-10"},
]


def _available(features, df):
    return [f for f in features if f in df.columns]


def _objective_onset(trial, df, features):
    """Optuna objective for onset model (focal loss)."""
    params = {
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 0.9),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 0.9),
        "min_child_weight": trial.suggest_int("min_child_weight", 5, 50),
        "gamma": trial.suggest_float("gamma", 0, 5),
        "reg_alpha": trial.suggest_float("reg_alpha", 0, 10),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10, log=True),
        "seed": RANDOM_SEED,
        "disable_default_eval_metric": True,
    }

    scores = []
    for fold in CV_FOLDS:
        train = df[df["date"] <= pd.Timestamp(fold["train_end"])]
        test = df[(df["date"] >= pd.Timestamp(fold["test_start"])) &
                  (df["date"] <= pd.Timestamp(fold["test_end"]))]

        train = train[train["dangerous_roll14d"] == 0]
        test = test[test["dangerous_roll14d"] == 0]

        if len(test) == 0 or test["label"].sum() == 0:
            continue

        dtrain = xgb.DMatrix(train[features].fillna(0), label=train["label"])
        dtest = xgb.DMatrix(test[features].fillna(0), label=test["label"])

        model = xgb.train(
            params, dtrain, num_boost_round=300,
            obj=focal_loss_objective, custom_metric=focal_eval_aucpr,
            evals=[(dtest, "val")], early_stopping_rounds=20, verbose_eval=0,
        )
        preds = expit(model.predict(dtest))
        scores.append(average_precision_score(test["label"], preds))

    return np.mean(scores) if scores else 0.0


def _objective_cont(trial, df, features):
    """Optuna objective for continuation model."""
    params = {
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 0.9),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 0.9),
        "min_child_weight": trial.suggest_int("min_child_weight", 5, 50),
        "gamma": trial.suggest_float("gamma", 0, 5),
        "reg_alpha": trial.suggest_float("reg_alpha", 0, 10),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10, log=True),
        "seed": RANDOM_SEED,
        "disable_default_eval_metric": True,
    }

    scores = []
    for fold in CV_FOLDS:
        train = df[df["date"] <= pd.Timestamp(fold["train_end"])]
        test = df[(df["date"] >= pd.Timestamp(fold["test_start"])) &
                  (df["date"] <= pd.Timestamp(fold["test_end"]))]

        train = train[train["dangerous_roll14d"] > 0]
        test = test[test["dangerous_roll14d"] > 0]

        if len(test) == 0 or test["label"].sum() == 0:
            continue

        n_pos = max((train["label"] == 1).sum(), 1)
        params["scale_pos_weight"] = (train["label"] == 0).sum() / n_pos

        model = xgb.XGBClassifier(**params, n_estimators=300,
                                   eval_metric="aucpr", early_stopping_rounds=20)
        model.fit(train[features].fillna(0), train["label"],
                  eval_set=[(test[features].fillna(0), test["label"])], verbose=False)
        preds = model.predict_proba(test[features].fillna(0))[:, 1]
        scores.append(average_precision_score(test["label"], preds))

    return np.mean(scores) if scores else 0.0


def tune():
    print("Loading data...")
    onset_df = pd.read_parquet(os.path.join(BASE, "data", "processed", "onset_set.parquet"))
    cont_df = pd.read_parquet(os.path.join(BASE, "data", "processed", "continuation_set.parquet"))
    master = pd.concat([onset_df, cont_df])

    onset_feats = _available(ONSET_FEATURES, master)
    cont_feats = _available(CONT_FEATURES, master)

    # ── Tune onset ────────────────────────────────────────────
    print(f"\nTuning ONSET model ({len(onset_feats)} features, 50 trials)...")
    onset_study = optuna.create_study(direction="maximize",
                                       study_name="onset_focal")
    onset_study.optimize(
        lambda trial: _objective_onset(trial, master, onset_feats),
        n_trials=50, show_progress_bar=True,
    )
    print(f"  Best onset CV AUC-PR: {onset_study.best_value:.4f}")
    print(f"  Best params: {onset_study.best_params}")

    # ── Tune continuation ─────────────────────────────────────
    print(f"\nTuning CONTINUATION model ({len(cont_feats)} features, 50 trials)...")
    cont_study = optuna.create_study(direction="maximize",
                                      study_name="continuation")
    cont_study.optimize(
        lambda trial: _objective_cont(trial, master, cont_feats),
        n_trials=50, show_progress_bar=True,
    )
    print(f"  Best cont CV AUC-PR: {cont_study.best_value:.4f}")
    print(f"  Best params: {cont_study.best_params}")

    # ── Save best params ──────────────────────────────────────
    import json
    params_path = os.path.join(BASE, "models", "best_hyperparams.json")
    os.makedirs(os.path.dirname(params_path), exist_ok=True)
    with open(params_path, "w") as f:
        json.dump({
            "onset": {"best_cv_aucpr": onset_study.best_value, **onset_study.best_params},
            "continuation": {"best_cv_aucpr": cont_study.best_value, **cont_study.best_params},
        }, f, indent=2)
    print(f"\nSaved: {params_path}")

    # ── Retrain with best params on full train set ────────────
    print("\nRetraining with best params on full training data...")

    # Onset (focal loss)
    train_onset = master[(master["date"] <= pd.Timestamp("2024-06-10")) &
                         (master["dangerous_roll14d"] == 0)]
    test_onset = master[(master["date"] >= pd.Timestamp("2024-07-01")) &
                        (master["dangerous_roll14d"] == 0)]

    best_onset_params = {**onset_study.best_params, "seed": RANDOM_SEED,
                         "disable_default_eval_metric": True}
    dtrain = xgb.DMatrix(train_onset[onset_feats].fillna(0), label=train_onset["label"])
    dtest = xgb.DMatrix(test_onset[onset_feats].fillna(0), label=test_onset["label"])

    onset_model = xgb.train(
        best_onset_params, dtrain, num_boost_round=500,
        obj=focal_loss_objective, custom_metric=focal_eval_aucpr,
        evals=[(dtest, "test")], early_stopping_rounds=30, verbose_eval=50,
    )
    onset_preds = expit(onset_model.predict(dtest))
    onset_aucpr = average_precision_score(test_onset["label"], onset_preds)
    onset_model.save_model(os.path.join(BASE, "models", "xgb_onset_tuned.ubj"))
    print(f"  Tuned onset AUC-PR: {onset_aucpr:.4f}")

    # Continuation
    train_cont = master[(master["date"] <= pd.Timestamp("2024-06-10")) &
                        (master["dangerous_roll14d"] > 0)]
    test_cont = master[(master["date"] >= pd.Timestamp("2024-07-01")) &
                       (master["dangerous_roll14d"] > 0)]

    best_cont_params = {**cont_study.best_params, "seed": RANDOM_SEED}
    n_pos = max((train_cont["label"] == 1).sum(), 1)
    best_cont_params["scale_pos_weight"] = (train_cont["label"] == 0).sum() / n_pos

    cont_model = xgb.XGBClassifier(**best_cont_params, n_estimators=500,
                                    eval_metric="aucpr", early_stopping_rounds=30)
    cont_model.fit(train_cont[cont_feats].fillna(0), train_cont["label"],
                   eval_set=[(test_cont[cont_feats].fillna(0), test_cont["label"])],
                   verbose=50)
    cont_preds = cont_model.predict_proba(test_cont[cont_feats].fillna(0))[:, 1]
    cont_aucpr = average_precision_score(test_cont["label"], cont_preds)
    cont_model.save_model(os.path.join(BASE, "models", "xgb_continuation_tuned.ubj"))
    print(f"  Tuned continuation AUC-PR: {cont_aucpr:.4f}")

    print(f"\n{'='*55}")
    print(f"  TUNING COMPLETE")
    print(f"  Onset:        {onset_aucpr:.4f}")
    print(f"  Continuation: {cont_aucpr:.4f}")
    print(f"{'='*55}")


if __name__ == "__main__":
    tune()
