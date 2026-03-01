export const TIER_COLORS = {
  CLEAR:   '#1a1a2e',   // dark navy — near invisible on dark map
  WATCH:   '#f6d860',   // yellow
  WARNING: '#f09438',   // orange
  DANGER:  '#e74c3c',   // red
}

export const TIER_OPACITY = {
  CLEAR:   0.15,
  WATCH:   0.55,
  WARNING: 0.70,
  DANGER:  0.85,
}

// Mapbox fill-color expression: matches tactical_tier to color
export const TIER_COLOR_EXPRESSION = [
  'match',
  ['get', 'tactical_tier'],
  'DANGER',  TIER_COLORS.DANGER,
  'WARNING', TIER_COLORS.WARNING,
  'WATCH',   TIER_COLORS.WATCH,
  TIER_COLORS.CLEAR,  // default
]

export const TIER_OPACITY_EXPRESSION = [
  'match',
  ['get', 'tactical_tier'],
  'DANGER',  TIER_OPACITY.DANGER,
  'WARNING', TIER_OPACITY.WARNING,
  'WATCH',   TIER_OPACITY.WATCH,
  TIER_OPACITY.CLEAR,
]

export const STRATEGIC_TIER_COLORS = {
  red:    '#e74c3c',
  orange: '#f09438',
  yellow: '#f6d860',
  green:  '#2ecc71',
}

// Strategic tier expressions (for backtest mode — uses ML scores)
export const STRATEGIC_COLOR_EXPRESSION = [
  'match',
  ['get', 'strategic_tier'],
  'red',    STRATEGIC_TIER_COLORS.red,
  'orange', STRATEGIC_TIER_COLORS.orange,
  'yellow', STRATEGIC_TIER_COLORS.yellow,
  '#1a1a2e',  // green/default
]

export const STRATEGIC_OPACITY_EXPRESSION = [
  'match',
  ['get', 'strategic_tier'],
  'red',    0.85,
  'orange', 0.70,
  'yellow', 0.55,
  0.15,
]
