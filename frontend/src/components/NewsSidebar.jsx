import { TIER_COLORS } from '../utils/tierColors'

export function NewsSidebar({ summary, loading, hidden }) {
  if (hidden) return null
  const showSkeleton = loading && !summary

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span style={styles.title}>AREA BRIEFING</span>
        {loading && <span style={styles.pulse}>updating…</span>}
      </div>

      {showSkeleton ? (
        <SkeletonLines />
      ) : !summary ? (
        <p style={styles.muted}>Pan the map to generate a conflict briefing for the visible area.</p>
      ) : (
        <>
          {/* Situation overview */}
          <div style={styles.section}>
            <div style={styles.label}>Situation Overview</div>
            <BriefingBody text={summary.briefing} />
          </div>

          {/* Threat distribution */}
          {summary.tier_counts && (
            <div style={styles.section}>
              <div style={styles.label}>Threat Distribution</div>
              <div style={styles.tiers}>
                {[
                  { key: 'RED', label: 'RED', color: '#e74c3c' },
                  { key: 'ORANGE', label: 'ORANGE', color: '#f09438' },
                  { key: 'YELLOW', label: 'YELLOW', color: '#f6d860' },
                  { key: 'GREEN', label: 'CLEAR', color: '#4a4a5a' },
                ].map(({ key, label, color }) => (
                  summary.tier_counts[key] > 0 && (
                    <div key={key} style={styles.tierRow}>
                      <span style={{
                        ...styles.tierBadge,
                        background: color,
                        color: key === 'YELLOW' ? '#222' : '#fff',
                      }}>{label}</span>
                      <span style={styles.tierCount}>{summary.tier_counts[key]} hexes</span>
                    </div>
                  )
                ))}
              </div>
            </div>
          )}

          {/* Citations from web search */}
          {summary.citations?.length > 0 && (
            <div style={styles.section}>
              <div style={styles.label}>Sources</div>
              {summary.citations.slice(0, 5).map((c, i) => (
                <a
                  key={i}
                  href={c.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.citation}
                >
                  <span style={styles.citationDot}>●</span>
                  <span style={styles.citationText}>{c.title}</span>
                </a>
              ))}
            </div>
          )}

          {/* Top triggers in area */}
          {summary.top_triggers?.length > 0 && (
            <div style={styles.section}>
              <div style={styles.label}>Active Signals</div>
              {summary.top_triggers.map((t, i) => (
                <div key={i} style={styles.trigger}>• {t}</div>
              ))}
            </div>
          )}

          {/* Hex coverage */}
          <div style={styles.footer}>
            {summary.hex_count} hexes in view · scored {summary.scored_at ? new Date(summary.scored_at).toLocaleTimeString() : '—'}
          </div>
        </>
      )}
    </div>
  )
}

/**
 * Render briefing text, splitting out any inline "Sources:" section
 * so we don't double-display citations.
 */
function BriefingBody({ text }) {
  if (!text) return null
  // Strip out "Sources:" section if Gemini included it inline
  const sourcesIdx = text.search(/\n\s*\*?\*?Sources:?\*?\*?\s*\n/i)
  const displayText = sourcesIdx > -1 ? text.slice(0, sourcesIdx).trim() : text
  return <p style={styles.body}>{displayText}</p>
}

function SkeletonLines() {
  return (
    <div>
      {[100, 85, 92, 70, 60].map((w, i) => (
        <div key={i} style={{ ...styles.skeleton, width: `${w}%`, marginBottom: 8 }} />
      ))}
    </div>
  )
}

const styles = {
  panel: {
    position: 'absolute',
    top: 16,
    right: 16,
    width: 300,
    maxHeight: 'calc(100vh - 32px)',
    overflowY: 'auto',
    background: '#12121f',
    border: '1px solid #2a2a3d',
    borderRadius: 8,
    padding: '16px 18px',
    color: '#ddd',
    fontFamily: 'system-ui, sans-serif',
    fontSize: 13,
    zIndex: 10,
    boxShadow: '0 4px 24px rgba(0,0,0,0.6)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 14,
  },
  title: {
    color: '#888',
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.1em',
  },
  pulse: {
    color: '#555',
    fontSize: 10,
    fontStyle: 'italic',
  },
  section: {
    marginBottom: 16,
  },
  label: {
    color: '#888',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginBottom: 8,
  },
  body: {
    margin: 0,
    color: '#ccc',
    lineHeight: 1.6,
  },
  tiers: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  tierRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  tierBadge: {
    padding: '2px 8px',
    borderRadius: 3,
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: '0.06em',
  },
  tierCount: {
    color: '#888',
    fontSize: 12,
  },
  citation: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    padding: '6px 0',
    color: '#7ab3ef',
    textDecoration: 'none',
    fontSize: 12,
    lineHeight: 1.4,
    borderBottom: '1px solid #1a1a2e',
    transition: 'color 0.15s',
  },
  citationDot: {
    color: '#4a6a8a',
    fontSize: 8,
    marginTop: 4,
    flexShrink: 0,
  },
  citationText: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  trigger: {
    color: '#aaa',
    marginBottom: 4,
    lineHeight: 1.4,
  },
  muted: {
    color: '#555',
    lineHeight: 1.5,
    margin: 0,
  },
  footer: {
    color: '#444',
    fontSize: 11,
    borderTop: '1px solid #2a2a3d',
    paddingTop: 10,
    marginTop: 4,
  },
  skeleton: {
    height: 12,
    borderRadius: 4,
    background: 'linear-gradient(90deg, #1a1a2e, #22223a, #1a1a2e)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.4s infinite',
  },
}
