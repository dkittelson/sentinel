import { useState, useEffect } from 'react'
import { getLang, toggleLang, onLangChange, t } from '../i18n'

/**
 * LangToggle — small button that switches between English and Arabic.
 * Forces a re-render of any component that imports useLang().
 */
export function LangToggle() {
  const lang = useLang()

  return (
    <button onClick={toggleLang} style={styles.btn}>
      {t('langToggle')}
    </button>
  )
}

/**
 * Hook to subscribe to language changes and trigger re-renders.
 */
export function useLang() {
  const [lang, setLang] = useState(getLang())

  useEffect(() => {
    return onLangChange(setLang)
  }, [])

  return lang
}

const styles = {
  btn: {
    background: 'transparent',
    border: '1px solid #555',
    borderRadius: 4,
    color: '#aaa',
    fontSize: 12,
    fontWeight: 700,
    padding: '3px 8px',
    cursor: 'pointer',
    fontFamily: 'system-ui, sans-serif',
    letterSpacing: '0.02em',
    transition: 'all 0.15s',
  },
}
