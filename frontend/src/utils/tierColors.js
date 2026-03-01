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

// ── Continuous gradient color expression ──────────────────────────────
// Interpolate strategic_score into a smooth danger gradient.
// Below 0.54 = clear (transparent). Above 0.54 ramps through:
//   0.54  light yellow
//   0.58  yellow
//   0.62  light orange
//   0.66  orange
//   0.70  red-orange
//   0.74  red
//   0.78+ dark red
export const STRATEGIC_COLOR_EXPRESSION = [
  'case',
  ['<', ['get', 'strategic_score'], 0.54],
  '#1a1a2e',  // clear — invisible on dark map
  [
    'interpolate',
    ['linear'],
    ['get', 'strategic_score'],
    0.54, '#f7f7a0',   // light yellow
    0.57, '#f6d860',   // yellow
    0.60, '#f0b840',   // gold
    0.63, '#f09438',   // orange
    0.66, '#e87830',   // deep orange
    0.69, '#e05a2c',   // red-orange
    0.72, '#d43d2a',   // red
    0.76, '#a81c20',   // dark red
    0.80, '#7a0c14',   // very dark red
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
    0.54, 0.40,
    0.60, 0.55,
    0.66, 0.65,
    0.72, 0.80,
    0.80, 0.90,
  ],
]
