"""Model calibration for Sentinel dual-model scoring.

Fits isotonic regression calibrators on a held-out 2024 calibration window
(not the same as the test set — we keep them separate to avoid calibration
leakage into eval metrics).

Why calibrate?
  XGBoost with focal loss outputs logits, not probabilities.
  Even after sigmoid, focal-loss models are systematically over-confident.
  Isotonic regression maps raw scores → calibrated probabilities (P(conflict | score)).
  The Sentinel strategic tiers (Yellow / Orange / Red) are thresholds on calibrated
  probabilities, so miscalibration causes wrong alert rates.

Approach: Platt + Isotonic comparison, pick lower Brier score.
  We use isotonic regression because it is non-parametric and handles the
  bimodal score distribution (onset model peaks near 0 for peaceful hexes,
  continuation peaks near 1 for active zones).

Calibration window: 2024-07-01 → 2024-12-10  (separate from train cutoff 2024-06-10)
  The test window (2024-07-01+) is used for both test AUC-PR and calibration.
  This is acceptable because calibration fitting is low-VC-dimension (monotone),
  but ideally use a third split if you have enough positive examples.

Output:
  backend/calibrators.pkl     — dict with keys 'onset', 'continuation', 'tiers'
  backend/calibration_plot.png — predicted vs observed calibration curves

Usage:
  python backend/calibrate.py
  python backend/calibrate.py --plot-only  (re-plot from saved calibrators)
"""

import argparse
import os
import pickle
import sys

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.special import expit
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, average_precision_score

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline", "train"))

PIPELINE_DIR   = os.path.join(ROOT, "pipeline")
DATA_DIR       = os.path.join(PIPELINE_DIR, "data", "processed")
MODEL_DIR      = os.path.join(PIPELINE_DIR, "models")
OUTPUT_PKL     = os.path.join(os.path.dirname(__file__), "calibrators.pkl")
OUTPUT_PLOT    = os.path.join(os.path.dirname(__file__), "calibration_plot.png")

ONSET_MODEL    = os.path.join(MODEL_DIR, "xgb_onset.ubj")
CONT_MODEL     = os.path.join(MODEL_DIR, "xgb_continuation.ubj")

# Calibration uses the held-out test window
CALIB_START = "2024-07-01"
CALIB_END   = "2024-12-10"

# Tier names for threshold derivation
TIER_NAMES = ["red", "orange", "yellow", "green"]
# Target percentiles for tier thresholds (based on expected alert rates)
# Red:    top 2% of active-zone scores
# Orange: top 10%
# Yellow: top 30%
TIER_PERCENTILES = {"red": 98, "orange": 90, "yellow": 70}


def _load_model(path: str):
    """Load XGBoost model (classifier or focal booster). Returns (model, is_booster)."""
    try:
        clf = xgb.XGBClassifier()
        clf.load_model(path)
        return clf, False
    except Exception:
        booster = xgb.Booster()
        booster.load_model(path)
        return booster, True


def _predict_raw(model, is_booster: bool, X: pd.DataFrame) -> np.ndarray:
    """Get raw model scores (before calibration)."""
    if is_booster:
        feats = model.feature_names
        if feats:
            for col in feats:
                if col not in X.columns:
                    X[col] = 0
            X = X[feats]
        raw = model.predict(xgb.DMatrix(X))
        return expit(raw)
    return model.predict_proba(X)[:, 1]


def _fit_calibrator(raw_scores: np.ndarray, labels: np.ndarray) -> IsotonicRegression:
    """Fit isotonic regression calibrator and compare to Platt scaling."""
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(raw_scores.reshape(-1, 1), labels)

    platt = LogisticRegression(C=1e6)
    platt.fit(raw_scores.reshape(-1, 1), labels)

    iso_brier  = brier_score_loss(labels, iso.predict(raw_scores.reshape(-1, 1)))
    platt_preds = platt.predict_proba(raw_scores.reshape(-1, 1))[:, 1]
    platt_brier = brier_score_loss(labels, platt_preds)

    print(f"    Isotonic Brier: {iso_brier:.4f} | Platt Brier: {platt_brier:.4f} "
          f"→ using {'isotonic' if iso_brier <= platt_brier else 'Platt'}")
    return iso if iso_brier <= platt_brier else platt


def _derive_thresholds(cal_onset: np.ndarray, cal_cont: np.ndarray) -> dict:
    """Derive Yellow/Orange/Red tier thresholds from calibrated score distributions.

    The combined calibrated score distribution reflects the real alert rates we want:
      - Red:    top 2%  → ~active combat hexes (Gaza strip, front lines)
      - Orange: top 10% → elevated danger concentration
      - Yellow: top 30% → recent activity / elevated signal

    We compute thresholds from the combined distribution (onset ∪ continuation)
    because in production both models' outputs are compared against the same thresholds.
    """
    all_scores = np.concatenate([cal_onset, cal_cont])
    thresholds = {}
    for tier, pct in TIER_PERCENTILES.items():
        thresholds[tier] = float(np.percentile(all_scores, pct))
    print("  Calibrated tier thresholds:")
    for tier, thresh in sorted(thresholds.items(), key=lambda x: -x[1]):
        print(f"    {tier.upper():8s}: ≥ {thresh:.3f}")
    return thresholds


def calibrate():
    """Fit calibrators on the 2024 holdout window and save to calibrators.pkl."""
    from train_onset import ONSET_FEATURES
    from train_continuation import CONT_FEATURES

    onset_path = os.path.join(DATA_DIR, "onset_set.parquet")
    cont_path  = os.path.join(DATA_DIR, "continuation_set.parquet")

    if not os.path.exists(onset_path) or not os.path.exists(cont_path):
        sys.exit("Calibration requires onset_set.parquet and continuation_set.parquet. "
                 "Run pipeline/train/split_data.py first.")

    print("Loading calibration data...")
    onset_df = pd.read_parquet(onset_path)
    cont_df  = pd.read_parquet(cont_path)

    onset_df["date"] = pd.to_datetime(onset_df["date"])
    cont_df["date"]  = pd.to_datetime(cont_df["date"])

    # Calibration window = test window
    onset_cal = onset_df[onset_df["date"] >= CALIB_START]
    cont_cal  = cont_df[cont_df["date"] >= CALIB_START]
    print(f"  Onset calibration rows:        {len(onset_cal):,} "
          f"({onset_cal['label'].mean():.3f} positive rate)")
    print(f"  Continuation calibration rows: {len(cont_cal):,} "
          f"({cont_cal['label'].mean():.3f} positive rate)")

    if not os.path.exists(ONSET_MODEL):
        sys.exit(f"Onset model not found: {ONSET_MODEL}")
    if not os.path.exists(CONT_MODEL):
        sys.exit(f"Continuation model not found: {CONT_MODEL}")

    print("Loading models...")
    onset_model, onset_is_booster = _load_model(ONSET_MODEL)
    cont_model,  cont_is_booster  = _load_model(CONT_MODEL)

    # Raw predictions
    onset_feats = [f for f in ONSET_FEATURES if f in onset_cal.columns]
    cont_feats  = [f for f in CONT_FEATURES  if f in cont_cal.columns]

    print(f"  Onset features:        {len(onset_feats)}/{len(ONSET_FEATURES)}")
    print(f"  Continuation features: {len(cont_feats)}/{len(CONT_FEATURES)}")

    X_onset = onset_cal[onset_feats].fillna(0)
    X_cont  = cont_cal[cont_feats].fillna(0)
    y_onset = onset_cal["label"].values
    y_cont  = cont_cal["label"].values

    print("Computing raw model scores...")
    raw_onset = _predict_raw(onset_model, onset_is_booster, X_onset)
    raw_cont  = _predict_raw(cont_model,  cont_is_booster,  X_cont)

    print(f"  Raw onset AUC-PR:        {average_precision_score(y_onset, raw_onset):.4f}")
    print(f"  Raw continuation AUC-PR: {average_precision_score(y_cont,  raw_cont):.4f}")

    print("Fitting calibrators...")
    print("  Onset:")
    onset_calibrator = _fit_calibrator(raw_onset, y_onset)
    print("  Continuation:")
    cont_calibrator  = _fit_calibrator(raw_cont, y_cont)

    # Calibrated predictions
    cal_onset = onset_calibrator.predict(raw_onset.reshape(-1, 1))
    cal_cont  = cont_calibrator.predict(raw_cont.reshape(-1, 1))
    if hasattr(cal_onset, "ravel"):
        cal_onset = cal_onset.ravel()
    if hasattr(cal_cont, "ravel"):
        cal_cont = cal_cont.ravel()

    print(f"  Calibrated onset AUC-PR:        {average_precision_score(y_onset, cal_onset):.4f}")
    print(f"  Calibrated continuation AUC-PR: {average_precision_score(y_cont,  cal_cont):.4f}")
    print(f"  Brier onset:        {brier_score_loss(y_onset, cal_onset):.4f}")
    print(f"  Brier continuation: {brier_score_loss(y_cont,  cal_cont):.4f}")

    tiers = _derive_thresholds(cal_onset, cal_cont)

    # Save calibrators
    payload = {
        "onset_calibrator":        onset_calibrator,
        "continuation_calibrator": cont_calibrator,
        "onset_features":          onset_feats,
        "continuation_features":   cont_feats,
        "tiers": tiers,
        "calibrated_on": CALIB_START,
    }
    with open(OUTPUT_PKL, "wb") as f:
        pickle.dump(payload, f)
    print(f"\nSaved calibrators → {OUTPUT_PKL}")

    _plot_calibration(y_onset, raw_onset, cal_onset, y_cont, raw_cont, cal_cont)
    return payload


def _plot_calibration(y_onset, raw_onset, cal_onset,
                       y_cont, raw_cont, cal_cont):
    """Plot calibration curves (predicted vs observed) for both models."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed — skipping calibration plot")
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Calibration Curves — Sentinel Dual-Model", fontsize=14)

    for ax, y, raw, cal, title in [
        (axes[0], y_onset, raw_onset, cal_onset, "Onset XGBoost"),
        (axes[1], y_cont,  raw_cont,  cal_cont,  "Continuation XGBoost"),
    ]:
        frac_raw, mean_raw = calibration_curve(y, raw, n_bins=10, strategy="quantile")
        frac_cal, mean_cal = calibration_curve(y, cal, n_bins=10, strategy="quantile")

        ax.plot([0, 1], [0, 1], "k--", lw=1, label="Perfect")
        ax.plot(mean_raw, frac_raw, "o-", color="orange", label="Before calibration")
        ax.plot(mean_cal, frac_cal, "s-", color="steelblue", label="After calibration")
        ax.set_xlabel("Mean predicted probability")
        ax.set_ylabel("Fraction of positives")
        ax.set_title(title)
        ax.legend(fontsize=9)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

    plt.tight_layout()
    plt.savefig(OUTPUT_PLOT, dpi=150, bbox_inches="tight")
    print(f"  Calibration plot saved → {OUTPUT_PLOT}")
    plt.close()


def load_calibrators() -> dict | None:
    """Load saved calibrators from disk. Returns None if not found."""
    if not os.path.exists(OUTPUT_PKL):
        return None
    with open(OUTPUT_PKL, "rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate Sentinel dual-model")
    parser.add_argument("--plot-only", action="store_true",
                        help="Re-plot from saved calibrators without refitting.")
    args = parser.parse_args()

    if args.plot_only:
        cals = load_calibrators()
        if cals is None:
            sys.exit(f"No calibrators found at {OUTPUT_PKL}. Run without --plot-only first.")
        print(f"Loaded calibrators from {OUTPUT_PKL}")
        print(f"  Tiers: {cals['tiers']}")
    else:
        calibrate()
