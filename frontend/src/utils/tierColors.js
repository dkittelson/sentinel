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

// ── Continuous heatmap gradient ───────────────────────────────────────
// Smooth thermal heatmap: clear → cool yellow → warm orange → hot red
// Score range in practice: 0.50 – 0.73
// Below 0.54 = no risk (transparent)
// 0.54–0.60 = low risk (cool pale yellow → warm yellow)
// 0.60–0.66 = moderate (yellow-orange → orange)
// 0.66–0.73+ = high risk (orange-red → deep red)
export const STRATEGIC_COLOR_EXPRESSION = [
  'case',
  ['<', ['get', 'strategic_score'], 0.54],
  'rgba(0,0,0,0)',  // clear — fully transparent
  [
    'interpolate',
    ['linear'],
    ['get', 'strategic_score'],
    0.54, '#ffffb2',   // pale warm yellow
    0.57, '#fed976',   // warm yellow
    0.60, '#feb24c',   // golden yellow
    0.63, '#fd8d3c',   // light orange
    0.65, '#fc4e2a',   // orange-red
    0.68, '#e31a1c',   // red
    0.71, '#bd0026',   // deep red
    0.74, '#800026',   // very dark red
  ],
]

export const STRATEGIC_OPACITY_EXPRESSION = [
  'case',
  ['<', ['get', 'strategic_score'], 0.54],
  0.0,   // fully transparent when clear
  [
    'interpolate',
    ['linear'],
    ['get', 'strategic_score'],
    0.54, 0.45,
    0.60, 0.58,
    0.66, 0.72,
    0.72, 0.85,
    0.80, 0.92,
  ],
]
