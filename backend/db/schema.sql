-- Sentinel DB Schema
-- Run this once in the Supabase SQL Editor before anything else.

-- Enable PostGIS for spatial queries
create extension if not exists postgis;

-- ── Static hex grid ───────────────────────────────────────────────────────────
-- Seeded once from acled_h3.csv (2,973 unique H3 hexes at resolution 6).
-- centroid is a PostGIS geography point used for radius queries.
create table if not exists hex_grid (
  h3_id    text primary key,
  centroid geography(Point, 4326),
  lat      float not null,
  lng      float not null
);

create index if not exists hex_grid_centroid_idx
  on hex_grid using gist(centroid);

-- ── Live risk scores ──────────────────────────────────────────────────────────
-- Updated every 15 minutes by 05_score_live.py.
-- strategic = XGBoost weekly model output
-- tactical  = rule-based immediate danger layer (tactical_alert.py)
create table if not exists risk_scores (
  h3_id             text primary key references hex_grid(h3_id),
  strategic_score   float,
  strategic_tier    text,                       -- green / yellow / orange / red
  tactical_score    float,
  tactical_tier     text,                       -- CLEAR / WATCH / WARNING / DANGER
  should_alert      boolean default false,
  tactical_triggers text,                       -- pipe-separated human-readable reasons
  alert_text        text,                       -- Gemini-generated (null unless DANGER)
  scored_at         timestamptz default now()
);

-- ── ACLED event log ───────────────────────────────────────────────────────────
-- Historical conflict events (written at ingestion, not updated at runtime).
create table if not exists acled_events (
  id           bigserial primary key,
  h3_id        text references hex_grid(h3_id),
  event_date   date,
  event_type   text,
  fatalities   int,
  actor1       text,
  latitude     float,
  longitude    float,
  ingested_at  timestamptz default now()
);

create index if not exists acled_events_h3_idx on acled_events(h3_id);
create index if not exists acled_events_date_idx on acled_events(event_date);

-- ── GDELT weekly aggregates ───────────────────────────────────────────────────
create table if not exists gdelt_signals (
  h3_id               text references hex_grid(h3_id),
  week                date,
  gdelt_event_count   int,
  gdelt_avg_tone      float,
  gdelt_hostility     float,
  gdelt_min_goldstein float,
  gdelt_num_articles  int,
  primary key (h3_id, week)
);

-- ── NASA FIRMS thermal anomaly aggregates ─────────────────────────────────────
create table if not exists firms_anomalies (
  h3_id               text references hex_grid(h3_id),
  week                date,
  firms_hotspot_count int,
  firms_avg_frp       float,
  firms_max_frp       float,
  firms_spike         int,
  primary key (h3_id, week)
);

-- ── Spatial query helper ──────────────────────────────────────────────────────
-- Called by GET /hexes/region in main.py.
-- Returns all hex IDs whose centroid is within radius_m metres of the given point.
create or replace function hexes_near_point(
  center_lat float,
  center_lon float,
  radius_m   float
)
returns table (h3_id text, lat float, lng float, distance_m float)
language sql stable
as $$
  select
    h3_id,
    lat,
    lng,
    st_distance(centroid, st_point(center_lon, center_lat)::geography) as distance_m
  from hex_grid
  where st_dwithin(
    centroid,
    st_point(center_lon, center_lat)::geography,
    radius_m
  )
  order by distance_m;
$$;
