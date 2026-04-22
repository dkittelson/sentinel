"""
05_score_live.py — Live Scoring Engine
=======================================
Loads the raw v1 CSV, applies the full v2 feature engineering pipeline
(publication lags, spatial recomputation, anomaly z-scores, etc.), then
runs dual-model scoring:
  - Peaceful hexes (dangerous_roll14d == 0): XGBoost onset model
  - Active hexes   (dangerous_roll14d  > 0): PerHexGRU continuation model
                                             (falls back to XGBoost if torch unavailable)

Results are upserted to Supabase risk_scores every 15 minutes by APScheduler.

Run from sentinel/ root:
    python backend/05_score_live.py
"""

import os
import sys
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.special import expit
from supabase import create_client
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from tactical_alert import score_hex

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Auto-pick richest available feature file (daily grain preferred)
_DATA_DIR = os.path.join(ROOT, "pipeline", "data", "processed")
for candidate in [
    "acled_h3_gdelt_firms_weather.csv",
    "acled_h3_gdelt_firms.csv",
    "acled_h3_gdelt.csv",
    "acled_h3.csv",
]:
    path = os.path.join(_DATA_DIR, candidate)
    if os.path.exists(path):
        FEATURE_PATH = path
        break
else:
    sys.exit("No processed feature file found. Run the pipeline first.")

_MODELS_DIR = os.path.join(ROOT, "pipeline", "models")
ONSET_MODEL_PATH        = os.path.join(_MODELS_DIR, "xgb_onset_tuned.ubj")
CONTINUATION_MODEL_PATH = os.path.join(_MODELS_DIR, "xgb_continuation_tuned.ubj")
MODEL_PATH              = os.path.join(_MODELS_DIR, "xgb_sentinel.ubj")  # v1 fallback

# ── Feature columns for the v1 fallback model only ───────────────────────────
BASE_FEATURES = [
    "event_count",
    "dangerous_count",
    "total_fatalities",
    "max_fatalities",
    "battle_count",
    "explosion_count",
    "vac_count",
    "riot_count",
    "population_best",
    "unique_actors",
    # Rolling windows: 3d, 7d, 14d
    "dangerous_roll3d",
    "dangerous_roll7d",
    "dangerous_roll14d",
    "fatalities_roll3d",
    "fatalities_roll7d",
    "fatalities_roll14d",
    "event_roll3d",
    "event_roll7d",
    "event_roll14d",
    # Velocity / momentum
    "dangerous_delta",
    "fatality_delta",
    "dangerous_velocity",
    "fatality_velocity",
    # Spatial lag
    "neighbor_danger_avg",
    "neighbor_fatal_sum",
    # Actor novelty
    "actor_pair_count",
    "actor_pair_delta",
    "actor_pair_velocity",
    # Temporal lags (yesterday / 2 days ago)
    "dangerous_lag1",
    "dangerous_lag2",
    "fatalities_lag1",
    "battle_lag1",
    "explosion_lag1",
]

GDELT_FEATURES = [
    "gdelt_event_count",
    "gdelt_avg_tone",
    "gdelt_min_goldstein",
    "gdelt_avg_goldstein",
    "gdelt_num_articles",
    "gdelt_hostility",
    "neighbor_gdelt_hostility_avg",
]

FIRMS_FEATURES = [
    "firms_hotspot_count",
    "firms_avg_frp",
    "firms_max_frp",
    "firms_spike",
    "neighbor_firms_spike_sum",
]

GDELT_CAMEO_FEATURES = [
    "gdelt_protest_count",
    "gdelt_threaten_count",
    "gdelt_assault_count",
    "gdelt_fight_count",
    "gdelt_cameo_conflict",
    "neighbor_gdelt_protest_avg",
]

WEATHER_FEATURES = [
    "temp_max",
    "temp_anomaly_30d",
    "precip_mm",
    "precip_spike",
]

# Strategic tier thresholds — fallback values for when calibrators.pkl is absent.
# When backend/calibrators.pkl exists (run backend/calibrate.py to generate it),
# these are replaced at startup with calibrated thresholds from the 2024 holdout.
_DEFAULT_TIERS = [
    (0.70, "red"),
    (0.63, "orange"),
    (0.54, "yellow"),
    (0.0,  "green"),
]

# Will be populated from calibrators.pkl at startup if available
STRATEGIC_TIERS = _DEFAULT_TIERS
_onset_calibrator = None
_cont_calibrator  = None


def _load_calibrators():
    """Load calibrators from disk and update tier thresholds."""
    global STRATEGIC_TIERS, _onset_calibrator, _cont_calibrator
    cal_path = os.path.join(os.path.dirname(__file__), "calibrators.pkl")
    if not os.path.exists(cal_path):
        return
    try:
        import pickle
        with open(cal_path, "rb") as f:
            cals = pickle.load(f)
        _onset_calibrator = cals.get("onset_calibrator")
        _cont_calibrator  = cals.get("continuation_calibrator")
        tiers = cals.get("tiers", {})
        if tiers:
            STRATEGIC_TIERS = [
                (tiers.get("red",    0.70), "red"),
                (tiers.get("orange", 0.63), "orange"),
                (tiers.get("yellow", 0.54), "yellow"),
                (0.0, "green"),
            ]
            print(f"  Calibrated tiers loaded: "
                  f"red≥{tiers['red']:.3f} "
                  f"orange≥{tiers['orange']:.3f} "
                  f"yellow≥{tiers['yellow']:.3f}")
    except Exception as exc:
        print(f"  Warning: calibrator load failed ({exc}) — using default thresholds")


def _apply_calibrator(calibrator, scores: np.ndarray) -> np.ndarray:
    """Apply a fitted calibrator to raw model scores. Safe no-op if None."""
    if calibrator is None:
        return scores
    try:
        cal = calibrator.predict(scores.reshape(-1, 1))
        return cal.ravel() if hasattr(cal, "ravel") else cal
    except Exception:
        return scores


def strategic_tier(score: float) -> str:
    for threshold, tier in STRATEGIC_TIERS:
        if score >= threshold:
            return tier
    return "green"


def load_model(path: str):
    """
    Load production model. Tries XGBClassifier first (standard),
    falls back to xgb.Booster (focal loss). Returns (model, is_booster).
    """
    try:
        clf = xgb.XGBClassifier()
        clf.load_model(path)
        return clf, False
    except Exception:
        booster = xgb.Booster()
        booster.load_model(path)
        return booster, True


def predict_proba(model, is_booster: bool, X: pd.DataFrame) -> np.ndarray:
    """Always returns values in [0,1]. Applies sigmoid to unbounded logits
    when the underlying XGBoost objective is raw (e.g. focal loss, or
    tuned classifiers saved with a logitraw objective)."""
    if is_booster:
        model_features = model.feature_names
        if model_features:
            for col in model_features:
                if col not in X.columns:
                    X[col] = 0
            X = X[model_features]
        raw = model.predict(xgb.DMatrix(X))
        return expit(raw)
    raw = model.predict_proba(X)[:, 1]
    # Some tuned classifiers were saved with logitraw objective — detect and
    # sigmoid them. A well-behaved predict_proba stays in [0,1]; anything
    # outside that range is a logit.
    if raw.min() < 0 or raw.max() > 1:
        return expit(raw)
    return raw


def _score_gru(gru_model, gru_scaler, gru_features, df_full, date_col, cont_mask, latest):
    """Build 14-day sequences for active hexes and run the GRU.

    Training fed the GRU (batch, seq_len=14, n_features) — we must reconstruct
    that same window at inference time, not just the latest single row.
    """
    import torch
    SEQ_LEN = 14

    df_full = df_full.sort_values(["h3_id", date_col])
    active_hex_ids = latest.loc[cont_mask, "h3_id"].values

    sequences = []
    hex_order = []
    for h3_id in active_hex_ids:
        hex_rows = df_full[df_full["h3_id"] == h3_id].tail(SEQ_LEN)
        # Keep ALL gru_features columns (not just those present in data) so the
        # tensor shape matches the model's input size. Missing columns → 0.
        for col in gru_features:
            if col not in hex_rows.columns:
                hex_rows[col] = 0.0
        if len(hex_rows) < SEQ_LEN:
            # Pad leading rows with zeros when hex has <14 days of history
            pad = pd.DataFrame(0.0, index=range(SEQ_LEN - len(hex_rows)),
                               columns=gru_features)
            hex_rows = pd.concat([pad, hex_rows[gru_features]], ignore_index=True)
        else:
            hex_rows = hex_rows[gru_features]
        sequences.append(hex_rows.fillna(0).values)
        hex_order.append(h3_id)

    if not sequences:
        return np.array([])

    X_seq = np.array(sequences, dtype=np.float32)  # (n_active, 14, n_features)
    # Reshape to (n_active * 14, n_features), scale, then reshape back
    n, t, f = X_seq.shape
    X_flat = X_seq.reshape(n * t, f)
    X_scaled = gru_scaler.transform(X_flat).reshape(n, t, f)

    with torch.no_grad():
        logits = gru_model(torch.tensor(X_scaled))
        probs = torch.sigmoid(logits).cpu().numpy()

    return probs


def run_scoring():
    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit("SUPABASE_URL and SUPABASE_KEY not set in backend/.env")

    _load_calibrators()
    print(f"Loading features from {FEATURE_PATH}...")
    df = pd.read_csv(FEATURE_PATH)
    date_col = next((c for c in ["date", "event_date", "week"] if c in df.columns), None)
    if date_col is None:
        sys.exit("No date column found in feature file (expected: date, event_date, or week)")
    df = df.rename(columns={date_col: "date"})
    date_col = "date"
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(["h3_id", date_col])

    # Apply the same feature engineering used at training time so production
    # features match exactly what the models were trained on.
    sys.path.insert(0, os.path.join(ROOT, "pipeline", "train"))
    from split_data import (
        _enforce_publication_lags,
        _merge_parquets,
        _add_derived_features,
        _add_anomaly_features,
        _add_interactions,
        _recompute_spatial_features,
    )
    print("  Applying v2 feature engineering pipeline...")
    df = _enforce_publication_lags(df)
    df = _recompute_spatial_features(df)
    df = _merge_parquets(df)
    df = _add_derived_features(df)
    df = _add_anomaly_features(df)
    df = _add_interactions(df)

    # Most recent record per hex (for onset / XGBoost cont scoring)
    latest = df.groupby("h3_id").last().reset_index()
    print(f"  {len(latest):,} hexes to score (latest date per hex)")

    # If dangerous_roll14d wasn't generated (e.g. pub-lag shifted it out),
    # add a zero-filled column so the onset/continuation split still works.
    if "dangerous_roll14d" not in latest.columns:
        latest["dangerous_roll14d"] = 0
        df["dangerous_roll14d"] = 0

    use_dual = (
        os.path.exists(ONSET_MODEL_PATH) and
        os.path.exists(CONTINUATION_MODEL_PATH)
    )

    # Check for GRU model for continuation
    GRU_MODEL_PATH = os.path.join(ROOT, "pipeline", "models", "perhexgru_best.pt")
    use_gru_cont = os.path.exists(GRU_MODEL_PATH)

    if use_dual:
        print("Using dual-model scoring (onset + continuation)...")
        onset_model, onset_is_booster = load_model(ONSET_MODEL_PATH)
        cont_model, cont_is_booster   = load_model(CONTINUATION_MODEL_PATH)

        # Derive feature lists from the models themselves so we never mismatch
        def _model_features(model, is_booster):
            feats = model.feature_names if is_booster else model.get_booster().feature_names
            return feats or []

        ONSET_FEATURES = _model_features(onset_model, onset_is_booster)
        CONT_FEATURES  = _model_features(cont_model,  cont_is_booster)

        # Use GRU for continuation if available
        if use_gru_cont:
            print("  Continuation: PerHexGRU (deep learning)")
            try:
                import torch
                from gnn_model import PerHexGRU
                from sklearn.preprocessing import StandardScaler
                checkpoint = torch.load(GRU_MODEL_PATH, map_location="cpu", weights_only=False)
                gru_features = checkpoint.get("features", CONT_FEATURES)
                gru_model = PerHexGRU(len(gru_features), hidden_dim=64, gru_layers=2)
                gru_model.load_state_dict(checkpoint["model_state_dict"])
                gru_model.eval()
                gru_scaler = StandardScaler()
                gru_scaler.mean_ = checkpoint["scaler_mean"]
                gru_scaler.scale_ = checkpoint["scaler_scale"]
                gru_scaler.n_features_in_ = len(gru_features)
            except Exception as e:
                print(f"  Warning: GRU load failed ({e}), falling back to XGBoost")
                use_gru_cont = False

        if not use_gru_cont:
            print("  Continuation: XGBoost")

        proba = np.zeros(len(latest))
        onset_mask = latest["dangerous_roll14d"] == 0
        cont_mask  = latest["dangerous_roll14d"] > 0

        # Only keep features present in data (model has priority; missing → 0)
        avail_onset = [f for f in ONSET_FEATURES if f in latest.columns]
        avail_cont  = [f for f in CONT_FEATURES  if f in latest.columns]

        onset_X = latest[onset_mask][avail_onset].fillna(0) if onset_mask.any() else None
        cont_X  = latest[cont_mask][avail_cont].fillna(0)  if cont_mask.any()  else None

        if onset_X is not None and len(onset_X) > 0:
            # Fill any features the model needs but data lacks
            for f in ONSET_FEATURES:
                if f not in onset_X.columns:
                    onset_X[f] = 0.0
            onset_X = onset_X[ONSET_FEATURES]
            raw_onset = predict_proba(onset_model, onset_is_booster, onset_X)
            proba[onset_mask.values] = _apply_calibrator(_onset_calibrator, raw_onset)
        if cont_X is not None and len(cont_X) > 0:
            if use_gru_cont:
                raw_cont = _score_gru(
                    gru_model, gru_scaler, gru_features, df, date_col, cont_mask, latest)
            else:
                for f in CONT_FEATURES:
                    if f not in cont_X.columns:
                        cont_X[f] = 0.0
                cont_X = cont_X[CONT_FEATURES]
                raw_cont = predict_proba(cont_model, cont_is_booster, cont_X)
            proba[cont_mask.values] = _apply_calibrator(_cont_calibrator, raw_cont)
    else:
        print(f"Falling back to v1 model from {MODEL_PATH}...")
        model, is_booster = load_model(MODEL_PATH)
        v1_features = [f for f in BASE_FEATURES + GDELT_FEATURES + FIRMS_FEATURES
                       + GDELT_CAMEO_FEATURES + WEATHER_FEATURES if f in latest.columns]
        X_v1 = latest[v1_features].fillna(0)
        proba = predict_proba(model, is_booster, X_v1)

    latest["strategic_score"] = proba

    # Percentile-based tier thresholds, recomputed from this run's distribution.
    # Stale fixed thresholds from a different model generation produced ~0 colored
    # hexes; percentile thresholds guarantee a meaningful gradient every run.
    global STRATEGIC_TIERS
    if len(proba) >= 100:
        p90, p95, p99 = np.percentile(proba, [90, 95, 99])
        STRATEGIC_TIERS = [
            (float(p99), "red"),
            (float(p95), "orange"),
            (float(p90), "yellow"),
            (0.0,        "green"),
        ]
        print(f"  Percentile tiers: red≥{p99:.4f} orange≥{p95:.4f} yellow≥{p90:.4f}")
    latest["strategic_tier"] = [strategic_tier(s) for s in proba]

    print("Running tactical scoring...")
    records = []
    for _, row in latest.iterrows():
        alert = score_hex(
            h3_id=row["h3_id"],
            firms_hotspot_count=row.get("firms_hotspot_count", 0),
            firms_avg_frp=row.get("firms_avg_frp", 0),
            firms_max_frp=row.get("firms_max_frp", 0),
            firms_spike=int(row.get("firms_spike", 0)),
            gdelt_hostility=row.get("gdelt_hostility", 0),
            gdelt_min_goldstein=row.get("gdelt_min_goldstein", 0),
            gdelt_avg_tone=row.get("gdelt_avg_tone", 0),
            gdelt_event_count=row.get("gdelt_event_count", 0),
            # daily column names → tactical_alert parameter names
            event_velocity=row.get("dangerous_velocity", row.get("event_velocity", 1.0)),
            neighbor_event_avg=row.get("neighbor_danger_avg", row.get("neighbor_event_avg", 0)),
            neighbor_fatal_sum=row.get("neighbor_fatal_sum", 0),
            strategic_score=float(row["strategic_score"]),
        )
        records.append({
            "h3_id":             row["h3_id"],
            "strategic_score":   round(float(row["strategic_score"]), 4),
            "strategic_tier":    row["strategic_tier"],
            "tactical_score":    alert.score,
            "tactical_tier":     alert.risk_level,
            "should_alert":      bool(alert.should_alert),
            "tactical_triggers": " | ".join(alert.triggers),
            "alert_text":        None,
        })

    import datetime
    scored_at = datetime.datetime.utcnow().isoformat() + "Z"

    print(f"Upserting {len(records):,} rows to risk_scores...")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    BATCH = 500
    for i in range(0, len(records), BATCH):
        client.table("risk_scores").upsert(records[i : i + BATCH]).execute()

    # Append to history table so the per-hex sparkline has data to draw.
    # Only stores the three columns the sparkline needs; cheap to write.
    history_rows = [
        {"h3_id": r["h3_id"], "strategic_score": r["strategic_score"],
         "strategic_tier": r["strategic_tier"], "scored_at": scored_at}
        for r in records
    ]
    print(f"Appending {len(history_rows):,} rows to risk_scores_history...")
    for i in range(0, len(history_rows), BATCH):
        client.table("risk_scores_history").insert(history_rows[i : i + BATCH]).execute()

    danger_count = sum(1 for r in records if r["tactical_tier"] == "DANGER")
    print(f"  Done. DANGER hexes this run: {danger_count}")

    # Gemini alert text for DANGER hexes
    if danger_count > 0:
        try:
            from alerting_agent import generate_alert
            danger_ids = {r["h3_id"] for r in records if r["tactical_tier"] == "DANGER"}
            print(f"Generating Gemini alerts for {len(danger_ids)} DANGER hexes...")
            for _, row in latest[latest["h3_id"].isin(danger_ids)].iterrows():
                alert_text = generate_alert(row.to_dict())
                if alert_text:
                    client.table("risk_scores").update(
                        {"alert_text": alert_text}
                    ).eq("h3_id", row["h3_id"]).execute()
        except Exception as e:
            print(f"  Warning: Gemini alert generation failed — {e}")

    return records


if __name__ == "__main__":
    run_scoring()
    print("Scoring complete.")
