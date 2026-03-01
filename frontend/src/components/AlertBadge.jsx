import { TIER_COLORS } from '../utils/tierColors'

const TIER_LABELS = {
  CLEAR:   'CLEAR',
  WATCH:   'WATCH',
  WARNING: 'WARNING',
  DANGER:  'DANGER',
}

export function AlertBadge({ tier }) {
  const color = TIER_COLORS[tier] || TIER_COLORS.CLEAR
  const isDark = tier === 'CLEAR'

  return (
    <span style={{
      display: 'inline-block',
      padding: '3px 10px',
      borderRadius: '4px',
      backgroundColor: color,
      color: isDark ? '#aaa' : '#fff',
      fontWeight: 700,
      fontSize: '12px',
      letterSpacing: '0.08em',
      border: isDark ? '1px solid #444' : 'none',
    }}>
      {TIER_LABELS[tier] || tier}
    </span>
  )
}
