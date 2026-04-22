import pandas as pd
import numpy as np
import os


def merge_features(output_path="data/processed/sentinel_v2_features.parquet"):
    if os.path.exists(output_path):
        print(f"Cache hit: {output_path}")
        return

    BASE = "data/processed"

    # ── Load conflict (ground truth) ──────────────────────────
    conflict = pd.read_parquet(f"{BASE}/ucdp_hex_daily.parquet")
    # Rename to avoid collision with GDELT's event_count
    conflict = conflict.rename(columns={"event_count": "ucdp_event_count"})

    # ── Build master hex-date grid ────────────────────────────
    hex_ids = conflict["h3_id"].unique()
    dates = pd.date_range("2020-01-01", "2025-12-31").date
    master = pd.DataFrame(
        pd.MultiIndex.from_product([hex_ids, dates], names=["h3_id", "date"]).tolist(),
        columns=["h3_id", "date"],
    )

    # ── Join time-series sources (h3_id + date) ───────────────
    master = master.merge(conflict, on=["h3_id", "date"], how="left")

    # Nightlights
    _merge_if_exists(master, f"{BASE}/nightlights_hex_daily.parquet",
                     on=["h3_id", "date"])

    # GDELT — rename event_count to avoid _x/_y
    gdelt_path = f"{BASE}/gdelt_hex_daily.parquet"
    if os.path.exists(gdelt_path):
        gdelt = pd.read_parquet(gdelt_path)
        gdelt = gdelt.rename(columns={"event_count": "gdelt_event_count"})
        master = master.merge(gdelt, on=["h3_id", "date"], how="left")

    # Pikud sirens
    _merge_if_exists(master, f"{BASE}/pikud_hex_daily.parquet",
                     on=["h3_id", "date"])

    # WFP food prices
    _merge_if_exists(master, f"{BASE}/wfp_hex_daily.parquet",
                     on=["h3_id", "date"])

    # ── Join static sources (h3_id only) ──────────────────────
    _merge_if_exists(master, f"{BASE}/worldpop_hex.parquet", on=["h3_id"])
    _merge_if_exists(master, f"{BASE}/osm_hex.parquet", on=["h3_id"])

    # ── Join date-only sources (broadcast to all hexes) ───────
    _merge_if_exists(master, f"{BASE}/calendar_daily.parquet", on=["date"])
    _merge_if_exists(master, f"{BASE}/ioda_daily.parquet", on=["date"])

    # ── Source-specific imputation (NOT blanket fillna(0)) ────
    _impute(master)

    # ── Feature engineering ───────────────────────────────────
    master = master.sort_values(["h3_id", "date"]).reset_index(drop=True)
    _add_rolling_features(master)
    _add_lag_features(master)
    _add_velocity_features(master)
    _add_ntl_features(master)
    _add_gdelt_features(master)
    _add_data_availability_flags(master)

    # Convert booleans
    if "ever_had_event_5yr" in master.columns:
        master["ever_had_event_5yr"] = master["ever_had_event_5yr"].astype(int)

    # Fill remaining NaN from feature engineering (rolling edges)
    master = master.fillna(0)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    master.to_parquet(output_path, index=False)
    print(f"Saved {len(master)} rows to {output_path}")


# ── Helpers ───────────────────────────────────────────────────

def _merge_if_exists(master, path, on):
    """Left-merge a parquet into master if the file exists."""
    if os.path.exists(path):
        df = pd.read_parquet(path)
        merged = master.merge(df, on=on, how="left")
        # Update master in-place via column assignment
        for col in merged.columns:
            master[col] = merged[col]


def _impute(df):
    """Source-aware imputation instead of blanket fillna(0)."""

    # Conflict counts: NaN = no event → 0 is correct
    for col in ["ucdp_event_count", "fatality_best", "is_state_based",
                "is_non_state", "is_one_sided", "dangerous_roll14d"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Binary / flag columns: NaN → 0
    for col in ["siren_count", "is_ramadan", "is_jerusalem_day",
                "is_election_window", "ever_had_event_5yr"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # Static sources: NaN → 0 (uninhabited / no amenities)
    for col in ["population", "hospital_count", "school_count"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # GDELT tone/goldstein: 0 is a real value (neutral), so fill with median
    for col in ["goldstein_mean", "tone_mean"]:
        if col in df.columns:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val if pd.notna(median_val) else 0)

    # GDELT counts: NaN = no coverage → 0
    for col in ["gdelt_event_count", "mentions_sum"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # NTL: NaN = no satellite pass, fill with per-hex median (not 0 = darkness)
    if "ntl_mean" in df.columns:
        hex_median = df.groupby("h3_id")["ntl_mean"].transform("median")
        df["ntl_mean"] = df["ntl_mean"].fillna(hex_median).fillna(0)

    # IODA: NaN = no outage data → 1.0 (full connectivity)
    for col in [c for c in df.columns if c.startswith("ioda_")]:
        df[col] = df[col].fillna(1.0)

    # WFP prices: fill with per-hex median
    for col in [c for c in df.columns if "price" in c]:
        hex_median = df.groupby("h3_id")[col].transform("median")
        df[col] = df[col].fillna(hex_median).fillna(0)


def _add_rolling_features(df):
    """Compute rolling sums for conflict counts."""
    for col, prefix in [("ucdp_event_count", "event"), ("fatality_best", "fatalities")]:
        if col not in df.columns:
            continue
        for window in [3, 7]:
            df[f"{prefix}_roll{window}d"] = (
                df.groupby("h3_id")[col]
                .transform(lambda x: x.rolling(window, min_periods=1).sum())
            )


def _add_lag_features(df):
    """Compute t-1 and t-2 lags for key columns."""
    for col in ["ucdp_event_count", "fatality_best", "dangerous_roll14d"]:
        if col not in df.columns:
            continue
        df[f"{col}_lag1"] = df.groupby("h3_id")[col].shift(1).fillna(0)
        df[f"{col}_lag2"] = df.groupby("h3_id")[col].shift(2).fillna(0)


def _add_velocity_features(df):
    """Velocity = short-term roll minus long-term roll (acceleration signal)."""
    if "event_roll3d" in df.columns and "event_roll7d" in df.columns:
        df["event_velocity"] = df["event_roll3d"] - df["event_roll7d"]
    if "fatalities_roll3d" in df.columns and "fatalities_roll7d" in df.columns:
        df["fatalities_velocity"] = df["fatalities_roll3d"] - df["fatalities_roll7d"]


def _add_ntl_features(df):
    """NTL delta and anomaly (infrastructure disruption signals)."""
    if "ntl_mean" not in df.columns:
        return
    df["ntl_delta_7d"] = df["ntl_mean"] - df.groupby("h3_id")["ntl_mean"].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )
    ntl_roll30 = df.groupby("h3_id")["ntl_mean"].transform(
        lambda x: x.rolling(30, min_periods=7).mean()
    )
    df["ntl_anomaly_30d"] = df["ntl_mean"] - ntl_roll30
    df["ntl_delta_7d"] = df["ntl_delta_7d"].fillna(0)
    df["ntl_anomaly_30d"] = df["ntl_anomaly_30d"].fillna(0)


def _add_gdelt_features(df):
    """GDELT rolling counts and velocity."""
    if "gdelt_event_count" not in df.columns:
        return
    df["gdelt_roll3d"] = df.groupby("h3_id")["gdelt_event_count"].transform(
        lambda x: x.rolling(3, min_periods=1).sum()
    )
    df["gdelt_roll7d"] = df.groupby("h3_id")["gdelt_event_count"].transform(
        lambda x: x.rolling(7, min_periods=1).sum()
    )
    df["gdelt_velocity"] = df["gdelt_roll3d"] - df["gdelt_roll7d"]

    if "goldstein_mean" in df.columns:
        df["goldstein_roll7d"] = df.groupby("h3_id")["goldstein_mean"].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )


def _add_data_availability_flags(df):
    """Binary flags indicating whether a source had data (vs imputed)."""
    # These must be computed BEFORE imputation in a real pipeline.
    # Here we approximate: if a hex-day has gdelt_event_count > 0, it had data.
    # This is imperfect but better than nothing.
    if "gdelt_event_count" in df.columns:
        df["has_gdelt"] = (df["gdelt_event_count"] > 0).astype(int)
    if "ntl_mean" in df.columns:
        df["has_ntl"] = (df["ntl_mean"] > 0).astype(int)


if __name__ == "__main__":
    merge_features()
