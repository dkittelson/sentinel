"""Load v1 CSV, apply all priority fixes, merge additional sources, split.

Priority fixes applied:
  1. Publication lag enforcement (ACLED=3d, GDELT=1d, FIRMS=3h)
  2. Recompute spatial features from scratch (verifiable H3 ring-1)
  3. Recency weighting for concept drift (post-Oct 7 2023)
  4. GDELT IDW interpolation to spread sparse signal to neighbors
  5. Domain-informed feature interactions
  6. Merge all available parquet sources
"""
import pandas as pd
import numpy as np
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml.config import (
    TRAIN_CUTOFF, TEST_START, LABEL_HORIZON_DAYS, PUB_LAGS,
    ZSCORE_WINDOW, ZSCORE_MIN_PERIODS, ZSCORE_CLIP, ANOMALY_THRESHOLD,
    RECENCY_HALFLIFE_DAYS, RECENCY_FLOOR, REGIME_CHANGE_DATE,
)

BASE = os.path.join(os.path.dirname(__file__), "..")
DATA_CSV = os.path.join(BASE, "data", "processed", "acled_h3_gdelt_firms_weather.csv")
PARQUET_DIR = os.path.join(BASE, "data", "processed")

# UCDP GED columns (30-day candidate lag — UCDP publishes provisional events monthly)
UCDP_COLS = [
    "ucdp_event_count", "ucdp_fatalities_best", "ucdp_fatalities_high",
    "ucdp_state_based", "ucdp_nonstate", "ucdp_onesided",
]

# ACLED-derived columns (need 3-day lag)
ACLED_COLS = [
    "event_count", "dangerous_count", "total_fatalities", "max_fatalities",
    "battle_count", "explosion_count", "vac_count", "riot_count",
    "unique_actors", "actor_pair_count",
    "dangerous_roll3d", "dangerous_roll7d", "dangerous_roll14d",
    "fatalities_roll3d", "fatalities_roll7d", "fatalities_roll14d",
    "event_roll3d", "event_roll7d", "event_roll14d",
    "dangerous_delta", "fatality_delta", "dangerous_velocity", "fatality_velocity",
    "actor_pair_delta", "actor_pair_roll14d", "actor_pair_velocity",
]

# GDELT-derived columns (need 1-day lag) — includes expanded events + GKG features
GDELT_COLS = [
    "gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
    "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility",
    # Events expansion
    "gdelt_num_sources", "gdelt_verbal_conflict", "gdelt_coop_fraction",
    "gdelt_cameo_conflict", "gdelt_protest_count", "gdelt_threaten_count",
    "gdelt_assault_count", "gdelt_fight_count",
    # GKG emotional dimensions
    "gdelt_fear_score", "gdelt_anger_score", "gdelt_anxiety_score",
    "gdelt_crisislex_count", "gdelt_arabic_count",
]


def _enforce_publication_lags(df):
    """Shift features forward by publication lag to simulate real-time availability.

    At scoring time t, ACLED data is only available through t-3.
    This shifts ACLED features so row t uses data from t-3.
    """
    print("  Enforcing publication lags...")
    df = df.sort_values(["h3_id", "date"])

    # ACLED: 3-day lag
    acled_present = [c for c in ACLED_COLS if c in df.columns]
    for col in acled_present:
        df[col] = df.groupby("h3_id")[col].shift(PUB_LAGS["acled"]).fillna(0)
    print(f"    ACLED: shifted {len(acled_present)} cols by {PUB_LAGS['acled']}d")

    # GDELT: 1-day lag
    gdelt_present = [c for c in GDELT_COLS if c in df.columns]
    for col in gdelt_present:
        df[col] = df.groupby("h3_id")[col].shift(PUB_LAGS["gdelt"]).fillna(0)
    print(f"    GDELT: shifted {len(gdelt_present)} cols by {PUB_LAGS['gdelt']}d")

    # UCDP: 30-day candidate lag (provisional events updated monthly)
    ucdp_present = [c for c in UCDP_COLS if c in df.columns]
    if ucdp_present:
        for col in ucdp_present:
            df[col] = df.groupby("h3_id")[col].shift(30).fillna(0)
        print(f"    UCDP: shifted {len(ucdp_present)} cols by 30d")

    # Note: dangerous_roll14d is lagged but still used for onset/continuation split.
    # This is correct: at scoring time, we know the 14-day rolling count from 3 days ago.
    return df


def _recompute_spatial_features(df):
    """Recompute neighbor features from scratch using H3 ring-1.

    Replaces the unknown-provenance neighbor_danger_avg and neighbor_fatal_sum
    from the v1 CSV with verifiable, properly-lagged spatial features.
    """
    try:
        import h3
    except ImportError:
        print("  Warning: h3 not installed, skipping spatial recomputation")
        return df

    print("  Recomputing spatial features from H3 ring-1 and ring-2...")

    # Build neighbor maps for ring-1 and ring-2
    hex_ids = df["h3_id"].unique()
    hex_set = set(hex_ids)
    neighbor_map = {}
    neighbor_map_r2 = {}
    for hid in hex_ids:
        try:
            r1 = list(h3.grid_ring(hid, 1))
            neighbor_map[hid] = [n for n in r1 if n in hex_set]
            r2 = list(h3.grid_ring(hid, 2))
            neighbor_map_r2[hid] = [n for n in r2 if n in hex_set]
        except Exception:
            neighbor_map[hid] = []

    # For each date, compute neighbor averages
    # Group by date for efficient lookup
    dates = df["date"].unique()
    n_dates = len(dates)

    # Pre-build lookup: (h3_id, date) -> values
    danger_col = "dangerous_count" if "dangerous_count" in df.columns else "event_count"
    fatal_col = "total_fatalities" if "total_fatalities" in df.columns else "max_fatalities"
    gdelt_host_col = "gdelt_hostility" if "gdelt_hostility" in df.columns else None

    # Use pivot for fast lookup
    print(f"    Building spatial index ({len(hex_ids)} hexes × {n_dates} dates)...")
    danger_pivot = df.pivot_table(index="date", columns="h3_id",
                                   values=danger_col, fill_value=0)
    fatal_pivot = df.pivot_table(index="date", columns="h3_id",
                                  values=fatal_col, fill_value=0)

    # Compute neighbor averages via matrix multiplication
    hex_list = list(danger_pivot.columns)
    hex_idx = {h: i for i, h in enumerate(hex_list)}
    n_hex = len(hex_list)

    # Build adjacency matrix (normalized by degree)
    adj = np.zeros((n_hex, n_hex), dtype=np.float32)
    for hid in hex_list:
        neighbors = neighbor_map.get(hid, [])
        if neighbors:
            idx = hex_idx[hid]
            for n in neighbors:
                if n in hex_idx:
                    adj[idx, hex_idx[n]] = 1.0 / len(neighbors)

    # Matrix multiply: neighbor_avg = data_matrix @ adj.T
    danger_matrix = danger_pivot.values.astype(np.float32)
    fatal_matrix = fatal_pivot.values.astype(np.float32)

    neighbor_danger = danger_matrix @ adj.T
    neighbor_fatal = fatal_matrix @ adj  # sum, not avg
    # For sum, use unnormalized adjacency
    adj_sum = np.zeros((n_hex, n_hex), dtype=np.float32)
    for hid in hex_list:
        neighbors = neighbor_map.get(hid, [])
        idx = hex_idx[hid]
        for n in neighbors:
            if n in hex_idx:
                adj_sum[idx, hex_idx[n]] = 1.0
    neighbor_fatal = fatal_matrix @ adj_sum.T

    # Convert back to dataframe
    nd_df = pd.DataFrame(neighbor_danger, index=danger_pivot.index,
                         columns=danger_pivot.columns)
    nf_df = pd.DataFrame(neighbor_fatal, index=fatal_pivot.index,
                         columns=fatal_pivot.columns)

    # Melt and merge back
    nd_melt = nd_df.reset_index().melt(id_vars="date", var_name="h3_id",
                                        value_name="neighbor_danger_recomp")
    nf_melt = nf_df.reset_index().melt(id_vars="date", var_name="h3_id",
                                        value_name="neighbor_fatal_recomp")

    df = df.merge(nd_melt, on=["date", "h3_id"], how="left")
    df = df.merge(nf_melt, on=["date", "h3_id"], how="left")

    # Replace old spatial features with recomputed ones
    df["neighbor_danger_avg"] = df["neighbor_danger_recomp"].fillna(0)
    df["neighbor_fatal_sum"] = df["neighbor_fatal_recomp"].fillna(0)
    df = df.drop(columns=["neighbor_danger_recomp", "neighbor_fatal_recomp"])

    # Also compute spatial gradient (max neighbor - self)
    if danger_col in df.columns:
        # Quick approximation: neighbor_danger_avg * degree gives approximate max
        df["spatial_gradient"] = df["neighbor_danger_avg"] - df[danger_col]
        df["spatial_gradient"] = df["spatial_gradient"].clip(lower=0).fillna(0)

    # GDELT spatial: spread sparse GDELT to neighbors
    if gdelt_host_col and gdelt_host_col in df.columns:
        host_pivot = df.pivot_table(index="date", columns="h3_id",
                                     values=gdelt_host_col, fill_value=0)
        host_matrix = host_pivot.values.astype(np.float32)
        neighbor_host = host_matrix @ adj.T
        nh_df = pd.DataFrame(neighbor_host, index=host_pivot.index,
                             columns=host_pivot.columns)
        nh_melt = nh_df.reset_index().melt(id_vars="date", var_name="h3_id",
                                            value_name="neighbor_gdelt_hostility_recomp")
        df = df.merge(nh_melt, on=["date", "h3_id"], how="left")
        df["neighbor_gdelt_hostility_avg"] = df["neighbor_gdelt_hostility_recomp"].fillna(0)
        df = df.drop(columns=["neighbor_gdelt_hostility_recomp"])

    # Ring-2 spatial features (wider spatial context)
    adj_r2 = np.zeros((n_hex, n_hex), dtype=np.float32)
    for hid in hex_list:
        neighbors_r2 = neighbor_map_r2.get(hid, [])
        if neighbors_r2:
            idx = hex_idx[hid]
            for n in neighbors_r2:
                if n in hex_idx:
                    adj_r2[idx, hex_idx[n]] = 1.0 / max(len(neighbors_r2), 1)

    neighbor_danger_r2 = danger_matrix @ adj_r2.T
    nd_r2_df = pd.DataFrame(neighbor_danger_r2, index=danger_pivot.index,
                            columns=danger_pivot.columns)
    nd_r2_melt = nd_r2_df.reset_index().melt(id_vars="date", var_name="h3_id",
                                              value_name="neighbor_danger_r2")
    df = df.merge(nd_r2_melt, on=["date", "h3_id"], how="left")
    df["neighbor_danger_r2"] = df["neighbor_danger_r2"].fillna(0)

    # FIRMS spatial: spread fire signal to neighbors
    if "firms_hotspot_count" in df.columns:
        firms_pivot = df.pivot_table(index="date", columns="h3_id",
                                      values="firms_hotspot_count", fill_value=0)
        firms_matrix = firms_pivot.values.astype(np.float32)
        neighbor_firms = firms_matrix @ adj.T
        nf_firms_df = pd.DataFrame(neighbor_firms, index=firms_pivot.index,
                                    columns=firms_pivot.columns)
        nf_firms_melt = nf_firms_df.reset_index().melt(
            id_vars="date", var_name="h3_id", value_name="neighbor_firms_avg_recomp")
        df = df.merge(nf_firms_melt, on=["date", "h3_id"], how="left")
        df["neighbor_firms_avg"] = df["neighbor_firms_avg_recomp"].fillna(0)
        df = df.drop(columns=["neighbor_firms_avg_recomp"])

    # NTL spatial: nightlight anomaly in neighbors
    if "ntl_mean" in df.columns:
        try:
            ntl_pivot = df.pivot_table(index="date", columns="h3_id",
                                        values="ntl_mean", fill_value=0)
            ntl_matrix = ntl_pivot.values.astype(np.float32)
            neighbor_ntl = ntl_matrix @ adj.T
            nn_df = pd.DataFrame(neighbor_ntl, index=ntl_pivot.index,
                                 columns=ntl_pivot.columns)
            nn_melt = nn_df.reset_index().melt(id_vars="date", var_name="h3_id",
                                                value_name="neighbor_ntl_avg")
            df = df.merge(nn_melt, on=["date", "h3_id"], how="left")
            df["neighbor_ntl_avg"] = df["neighbor_ntl_avg"].fillna(0)
        except Exception:
            pass

    print(f"    Recomputed: ring-1 + ring-2 spatial features for "
          f"danger, fatalities, GDELT hostility, FIRMS, NTL")
    return df


def _add_recency_weights(df):
    """Add sample weights: exponential decay favoring recent data.

    Post-Oct 7 2023 conflict dynamics are fundamentally different.
    Recent data should matter more.
    """
    print("  Adding recency weights...")
    regime_date = pd.Timestamp(REGIME_CHANGE_DATE)
    df["days_since_regime"] = (df["date"] - regime_date).dt.days
    df["post_oct7"] = (df["date"] >= regime_date).astype(int)

    # Exponential decay: recent data weighted higher (conflict dynamics shifted post-Oct-7)
    max_date = df["date"].max()
    days_from_end = (max_date - df["date"]).dt.days
    df["sample_weight"] = np.exp(-0.5 * days_from_end / RECENCY_HALFLIFE_DAYS).astype(np.float32)
    df["sample_weight"] = df["sample_weight"].clip(lower=RECENCY_FLOOR)

    print(f"    post_oct7 flag, sample_weight (min={df['sample_weight'].min():.2f}, "
          f"max={df['sample_weight'].max():.2f})")
    return df


def _add_anomaly_features(df):
    """Z-scores, residuals, acceleration — anomaly detection framing for onset.

    Instead of predicting "will there be conflict?" from absolute values,
    this asks "how unusual is today compared to this hex's baseline?"
    This is how CDC EARS and BioSense detect disease outbreaks.
    """
    print("  Adding anomaly detection features...")
    df = df.sort_values(["h3_id", "date"])

    # Z-score features: (value - Nd_mean) / Nd_std
    # Asks "how unusual is today vs this hex's recent baseline?" (anomaly detection framing)
    zscore_name = {
        "gdelt_hostility":     "gdelt_hostility_zscore",
        "gdelt_event_count":   "gdelt_event_count_zscore",
        "gdelt_fear_score":    "gdelt_fear_zscore",
        "gdelt_anger_score":   "gdelt_anger_zscore",
        "gdelt_arabic_count":  "gdelt_arabic_zscore",
        "neighbor_danger_avg": "neighbor_danger_zscore",
        "lbp_usd_parallel":   "lbp_zscore",
        "firms_hotspot_count": "firms_zscore",
        "ntl_mean":            "ntl_zscore",
        "siren_count":         "siren_zscore",
        "damage_mean":         "damage_zscore",
    }
    zscore_cols = []
    for col, zname in zscore_name.items():
        if col not in df.columns:
            continue
        roll_mean = df.groupby("h3_id")[col].transform(
            lambda x: x.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).mean())
        roll_std = df.groupby("h3_id")[col].transform(
            lambda x: x.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).std())
        df[zname] = ((df[col] - roll_mean) / roll_std.clip(lower=1e-6)).fillna(0)
        df[zname] = df[zname].clip(-ZSCORE_CLIP, ZSCORE_CLIP)
        zscore_cols.append(zname)

    # Residual features: value - Nd_median (deviation from hex-specific typical level)
    residual_name = {
        "gdelt_hostility":   "gdelt_hostility_residual",
        "neighbor_danger_avg":"neighbor_danger_residual",
        "lbp_usd_parallel":  "lbp_residual",
    }
    for col, rname in residual_name.items():
        if col not in df.columns:
            continue
        roll_med = df.groupby("h3_id")[col].transform(
            lambda x: x.rolling(ZSCORE_WINDOW, min_periods=ZSCORE_MIN_PERIODS).median())
        df[rname] = (df[col] - roll_med).fillna(0)

    # Acceleration features: second derivative (is the velocity itself changing?)
    if "gdelt_hostility_velocity" in df.columns:
        df["gdelt_hostility_accel"] = df.groupby("h3_id")["gdelt_hostility_velocity"].diff().fillna(0)
    if "neighbor_danger_avg" in df.columns:
        lag1 = df.groupby("h3_id")["neighbor_danger_avg"].shift(1).fillna(0)
        lag2 = df.groupby("h3_id")["neighbor_danger_avg"].shift(2).fillna(0)
        df["neighbor_danger_accel"] = (df["neighbor_danger_avg"] - lag1) - (lag1 - lag2)
        df["neighbor_danger_accel"] = df["neighbor_danger_accel"].fillna(0)
    if "lbp_change_7d" in df.columns:
        df["lbp_accel"] = df.groupby("h3_id")["lbp_change_7d"].diff(7).fillna(0)

    # Cross-feature anomaly composites
    if zscore_cols:
        zscore_df = df[zscore_cols].abs()
        df["anomaly_count"] = (zscore_df > ANOMALY_THRESHOLD).sum(axis=1).astype(int)
        df["max_anomaly"] = zscore_df.max(axis=1).fillna(0)

    n_new = sum(1 for c in ["gdelt_hostility_zscore", "gdelt_event_count_zscore",
                             "neighbor_danger_zscore", "lbp_zscore",
                             "gdelt_hostility_residual", "neighbor_danger_residual",
                             "lbp_residual", "gdelt_hostility_accel",
                             "neighbor_danger_accel", "lbp_accel",
                             "anomaly_count", "max_anomaly"] if c in df.columns)
    print(f"    Added {n_new} anomaly features")
    return df


def _add_interactions(df):
    """Domain-informed feature interactions."""
    print("  Adding interaction features...")
    interactions = []

    if "gdelt_hostility" in df.columns and "neighbor_danger_avg" in df.columns:
        df["hostility_x_neighbor_danger"] = df["gdelt_hostility"] * df["neighbor_danger_avg"]
        interactions.append("hostility_x_neighbor_danger")

    if "ntl_delta_7d" in df.columns and "firms_spike" in df.columns:
        df["ntl_drop_x_fire"] = df["ntl_delta_7d"].clip(upper=0).abs() * df["firms_spike"]
        interactions.append("ntl_drop_x_fire")

    if "lbp_volatility_7d" in df.columns and "ipc_crisis_flag" in df.columns:
        df["economic_stress"] = df["lbp_volatility_7d"] * df["ipc_crisis_flag"]
        interactions.append("economic_stress")

    if "gdelt_hostility" in df.columns and "siren_count" in df.columns:
        df["hostility_x_sirens"] = df["gdelt_hostility"] * df["siren_count"]
        interactions.append("hostility_x_sirens")

    if interactions:
        print(f"    Added: {', '.join(interactions)}")
    return df


def _merge_parquets(df):
    """Merge all available parquet sources."""
    print("Merging additional sources...")

    # Nightlights
    ntl_path = os.path.join(PARQUET_DIR, "nightlights_hex_daily.parquet")
    if os.path.exists(ntl_path):
        ntl = pd.read_parquet(ntl_path)
        ntl["date"] = pd.to_datetime(ntl["date"])
        df = df.merge(ntl, on=["h3_id", "date"], how="left")
        hex_median = df.groupby("h3_id")["ntl_mean"].transform("median")
        df["ntl_mean"] = df["ntl_mean"].fillna(hex_median).fillna(0)
        print(f"  + nightlights: ntl_mean")

    # Pikud sirens
    pikud_path = os.path.join(PARQUET_DIR, "pikud_hex_daily.parquet")
    if os.path.exists(pikud_path):
        pikud = pd.read_parquet(pikud_path)
        pikud["date"] = pd.to_datetime(pikud["date"])
        df = df.merge(pikud, on=["h3_id", "date"], how="left")
        df["siren_count"] = df["siren_count"].fillna(0)
        print(f"  + pikud sirens")

    # Calendar
    cal_path = os.path.join(PARQUET_DIR, "calendar_daily.parquet")
    if os.path.exists(cal_path):
        cal = pd.read_parquet(cal_path)
        cal["date"] = pd.to_datetime(cal["date"])
        df = df.merge(cal, on="date", how="left")
        cal_cols = [c for c in cal.columns if c != "date"]
        for col in cal_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        print(f"  + calendar: {len(cal_cols)} features")

    # WorldPop
    wp_path = os.path.join(PARQUET_DIR, "worldpop_hex.parquet")
    if os.path.exists(wp_path):
        wp = pd.read_parquet(wp_path)
        if "population" in wp.columns:
            wp = wp.rename(columns={"population": "worldpop_population"})
        df = df.merge(wp, on="h3_id", how="left")
        if "worldpop_population" in df.columns:
            df["worldpop_population"] = df["worldpop_population"].fillna(0)
        print(f"  + worldpop")

    # OSM
    osm_path = os.path.join(PARQUET_DIR, "osm_hex.parquet")
    if os.path.exists(osm_path):
        osm = pd.read_parquet(osm_path)
        df = df.merge(osm, on="h3_id", how="left")
        for col in ["hospital_count", "school_count"]:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        print(f"  + osm")

    # LBP exchange rate + date-keyed sources
    for name, filename in [("lbp", "lbp_daily.parquet"), ("ipc", "ipc_daily.parquet"),
                           ("gtrends", "gtrends_daily.parquet"),
                           ("cloudflare", "cloudflare_daily.parquet")]:
        path = os.path.join(PARQUET_DIR, filename)
        if os.path.exists(path):
            src = pd.read_parquet(path)
            src["date"] = pd.to_datetime(src["date"])
            df = df.merge(src, on="date", how="left")
            new_cols = [c for c in src.columns if c != "date"]
            for col in new_cols:
                if col in df.columns:
                    df[col] = df[col].fillna(0)
            print(f"  + {name}: {len(new_cols)} features")

    # UCDP GED (CC BY 4.0 ground-truth, independent of ACLED)
    ucdp_path = os.path.join(PARQUET_DIR, "ucdp_hex_daily.parquet")
    if os.path.exists(ucdp_path):
        ucdp = pd.read_parquet(ucdp_path)
        ucdp["date"] = pd.to_datetime(ucdp["date"])
        df = df.merge(ucdp, on=["h3_id", "date"], how="left")
        for col in UCDP_COLS:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        print(f"  + ucdp: {len(UCDP_COLS)} features")

    # GDELT expanded events + GKG emotional dims
    gdelt_path = os.path.join(PARQUET_DIR, "gdelt_hex_daily.parquet")
    if os.path.exists(gdelt_path):
        gdelt = pd.read_parquet(gdelt_path)
        gdelt["date"] = pd.to_datetime(gdelt["date"])
        # Only merge columns not already present in df (avoids overwriting CSV columns)
        new_gdelt_cols = [c for c in gdelt.columns
                          if c not in ("h3_id", "date") and c not in df.columns]
        if new_gdelt_cols:
            gdelt_sub = gdelt[["h3_id", "date"] + new_gdelt_cols]
            df = df.merge(gdelt_sub, on=["h3_id", "date"], how="left")
            for col in new_gdelt_cols:
                df[col] = df[col].fillna(0)
            print(f"  + gdelt GKG: {len(new_gdelt_cols)} new features "
                  f"({', '.join(new_gdelt_cols[:4])}...)")

    # SAR battle damage (PWTT Sentinel-1)
    sar_path = os.path.join(PARQUET_DIR, "sar_damage_hex_daily.parquet")
    if os.path.exists(sar_path):
        sar = pd.read_parquet(sar_path)
        sar["date"] = pd.to_datetime(sar["date"])
        sar_cols = [c for c in sar.columns if c not in ("h3_id", "date")]
        df = df.merge(sar, on=["h3_id", "date"], how="left")
        for col in sar_cols:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        print(f"  + SAR damage: {', '.join(sar_cols)}")

    return df


def _add_derived_features(df):
    """Compute rolling, velocity, and derived features."""
    print("Computing derived features...")
    df = df.sort_values(["h3_id", "date"])

    # NTL dynamics
    if "ntl_mean" in df.columns:
        df["ntl_delta_7d"] = df["ntl_mean"] - df.groupby("h3_id")["ntl_mean"].transform(
            lambda x: x.rolling(7, min_periods=1).mean())
        df["ntl_anomaly_30d"] = df["ntl_mean"] - df.groupby("h3_id")["ntl_mean"].transform(
            lambda x: x.rolling(30, min_periods=7).mean())
        df["ntl_delta_7d"] = df["ntl_delta_7d"].fillna(0)
        df["ntl_anomaly_30d"] = df["ntl_anomaly_30d"].fillna(0)

    # GDELT dynamics
    if "gdelt_hostility" in df.columns:
        df["gdelt_hostility_roll3d"] = df.groupby("h3_id")["gdelt_hostility"].transform(
            lambda x: x.rolling(3, min_periods=1).mean())
        df["gdelt_hostility_roll7d"] = df.groupby("h3_id")["gdelt_hostility"].transform(
            lambda x: x.rolling(7, min_periods=1).mean())
        df["gdelt_hostility_velocity"] = df["gdelt_hostility_roll3d"] - df["gdelt_hostility_roll7d"]

    if "gdelt_event_count" in df.columns:
        df["gdelt_event_roll3d"] = df.groupby("h3_id")["gdelt_event_count"].transform(
            lambda x: x.rolling(3, min_periods=1).sum())
        df["gdelt_event_roll7d"] = df.groupby("h3_id")["gdelt_event_count"].transform(
            lambda x: x.rolling(7, min_periods=1).sum())
        df["gdelt_event_velocity"] = df["gdelt_event_roll3d"] - df["gdelt_event_roll7d"]

    if "gdelt_avg_tone" in df.columns:
        tone_7d = df.groupby("h3_id")["gdelt_avg_tone"].transform(
            lambda x: x.rolling(7, min_periods=1).mean())
        df["gdelt_tone_delta"] = df["gdelt_avg_tone"] - tone_7d

    # Fill NaN from rolling
    for col in df.columns:
        if any(k in col for k in ["roll", "velocity", "delta", "anomaly"]):
            df[col] = df[col].fillna(0)

    print(f"  Derived features added")
    return df


def split_data():
    out_dir = PARQUET_DIR
    onset_path = os.path.join(out_dir, "onset_set.parquet")
    cont_path = os.path.join(out_dir, "continuation_set.parquet")

    if os.path.exists(onset_path) and os.path.exists(cont_path):
        print("Cache hit: split already done")
        return

    # ── Load v1 CSV ───────────────────────────────────────────
    print(f"Loading {DATA_CSV}...")
    df = pd.read_csv(DATA_CSV, parse_dates=["event_date"])
    df = df.rename(columns={"event_date": "date"})
    print(f"  {len(df):,} rows, {df['h3_id'].nunique()} hexes, {len(df.columns)} cols")

    # ── Priority Fix 1: Publication lag enforcement ───────────
    df = _enforce_publication_lags(df)

    # ── Priority Fix 2: Recompute spatial features ────────────
    df = _recompute_spatial_features(df)

    # ── Merge additional parquet sources ───────────────────────
    df = _merge_parquets(df)

    # ── Compute derived features ──────────────────────────────
    df = _add_derived_features(df)

    # ── Priority Fix 5: Feature interactions ──────────────────
    df = _add_anomaly_features(df)
    df = _add_interactions(df)

    # ── Priority Fix 8: Recency weighting ─────────────────────
    df = _add_recency_weights(df)

    print(f"  Final: {len(df.columns)} columns")

    # ── Recompute label ───────────────────────────────────────
    df = df.sort_values(["h3_id", "date"])
    horizon = LABEL_HORIZON_DAYS
    print(f"Label horizon: {horizon} days")
    future_danger = pd.Series(0.0, index=df.index)
    for i in range(1, horizon + 1):
        future_danger += df.groupby("h3_id")["dangerous_count"].shift(-i).fillna(0)
    df["label"] = (future_danger > 0).astype(int)
    print(f"  Label dist: {df['label'].value_counts().to_dict()}")

    # ── Temporal gap ──────────────────────────────────────────
    train_cutoff = pd.Timestamp(TRAIN_CUTOFF)
    test_start = pd.Timestamp(TEST_START)
    before = len(df)
    df = df[(df["date"] <= train_cutoff) | (df["date"] >= test_start)]
    print(f"  Gap: removed {before - len(df):,} rows")

    # ── Split ─────────────────────────────────────────────────
    onset = df[df["dangerous_roll14d"] == 0].copy()
    continuation = df[df["dangerous_roll14d"] > 0].copy()

    os.makedirs(out_dir, exist_ok=True)
    onset.to_parquet(onset_path, index=False)
    continuation.to_parquet(cont_path, index=False)
    print(f"  Onset: {len(onset):,} rows ({onset['label'].mean()*100:.2f}% pos), {len(onset.columns)} cols")
    print(f"  Continuation: {len(continuation):,} rows ({continuation['label'].mean()*100:.2f}% pos)")


if __name__ == "__main__":
    split_data()
