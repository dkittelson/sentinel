BASE_FEATURES = [
    "event_count", "dangerous_count", "total_fatalities", "max_fatalities",
    "battle_count", "explosion_count", "vac_count", "riot_count",
    "population_best", "unique_actors",
    "dangerous_roll3d", "dangerous_roll7d", "dangerous_roll14d",
    "fatalities_roll3d", "fatalities_roll7d", "fatalities_roll14d",
    "event_roll3d", "event_roll7d", "event_roll14d",
    "dangerous_delta", "fatality_delta", "dangerous_velocity", "fatality_velocity",
    "neighbor_danger_avg", "neighbor_fatal_sum",
    "actor_pair_count", "actor_pair_delta", "actor_pair_velocity",
    "dangerous_lag1", "dangerous_lag2", "fatalities_lag1", "battle_lag1", "explosion_lag1",
]

GDELT_FEATURES = [
    "gdelt_event_count", "gdelt_avg_tone", "gdelt_min_goldstein",
    "gdelt_avg_goldstein", "gdelt_num_articles", "gdelt_hostility",
    "neighbor_gdelt_hostility_avg",
]

FIRMS_FEATURES = [
    "firms_hotspot_count", "firms_avg_frp", "firms_max_frp", "firms_spike",
    "neighbor_firms_spike_sum",
]

WEATHER_FEATURES = [
    "temp_max", "temp_anomaly_30d", "precip_mm", "precip_spike",
]

ALL_FEATURES = BASE_FEATURES + GDELT_FEATURES + FIRMS_FEATURES + WEATHER_FEATURES

def get_available_features(df):
    subset_features = []
    for feature in ALL_FEATURES:
        if feature in df:
            subset_features.append(feature)

    return subset_features