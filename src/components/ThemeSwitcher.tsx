import { useState, useEffect } from 'react'
import { Palette, Check, RotateCcw } from 'lucide-react'
import { useTranslation } from '../lib/i18n'

export type ThemeId = 'emerald' | 'cyber' | 'solar' | 'royal'

interface ThemeOption {
  id: ThemeId
  nameEn: string
  nameTe: string
  dot: string
  accent: string
}

const THEMES: ThemeOption[] = [
  {
    id: 'emerald',
    nameEn: 'Emerald Biotech',
    nameTe: 'బయో ఎమరాల్డ్ (డిఫాల్ట్)',
    dot: '#10b981',
    accent: '#34d399',
  },
  {
    id: 'cyber',
    nameEn: 'Cyber Agritech (Default)',
    nameTe: 'సైబర్ అగ్రిటెక్ (నీలి రంగు)',
    dot: '#06b6d4',
    accent: '#a3e635',
  },
  {
    id: 'solar',
    nameEn: 'Golden Harvest',
    nameTe: 'గోల్డెన్ హార్వెస్ట్ (బంగారు కాంతి)',
    dot: '#f59e0b',
    accent: '#ea580c',
  },
  {
    id: 'royal',
    nameEn: 'Agro Amethyst',
    nameTe: 'రాయల్ వైలెట్ (ఊదా రంగు)',
    dot: '#a855f7',
    accent: '#10b981',
  },
]

export function ThemeSwitcher() {
  const { language } = useTranslation()
  const [currentTheme, setCurrentTheme] = useState<ThemeId>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('agrivision-theme') as ThemeId) || 'cyber'
    }
    return 'cyber'
  })
  const [open, setOpen] = useState(false)

  const applyTheme = (theme: ThemeId) => {
    setCurrentTheme(theme)
    if (typeof document !== 'undefined') {
      if (theme === 'emerald') {
        document.documentElement.removeAttribute('data-theme')
      } else {
        document.documentElement.setAttribute('data-theme', theme)
      }
      localStorage.setItem('agrivision-theme', theme)
    }
    setOpen(false)
  }

  useEffect(() => {
    const saved = localStorage.getItem('agrivision-theme') as ThemeId
    if (saved && saved !== 'emerald') {
      document.documentElement.setAttribute('data-theme', saved)
    } else if (!saved) {
      document.documentElement.setAttribute('data-theme', 'cyber')
    }
  }, [])

  const activeThemeObj = THEMES.find(t => t.id === currentTheme) || THEMES[0]

  return (
    <div className="theme-switcher" style={{ position: 'relative', display: 'inline-block' }}>
      <button
        className="theme-switcher-trigger"
        onClick={() => setOpen(!open)}
        title="Experiment Color Themes"
        aria-label="Experiment Color Themes"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(12, 24, 36, 0.95)',
          border: `1.5px solid ${activeThemeObj.dot}`,
          borderRadius: '20px',
          padding: '6px 14px',
          color: '#ffffff',
          fontSize: '12px',
          fontWeight: 700,
          cursor: 'pointer',
          boxShadow: `0 0 12px ${activeThemeObj.dot}40`,
          transition: 'all 0.2s ease',
        }}
      >
        <span
          style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: activeThemeObj.dot,
            boxShadow: `0 0 8px ${activeThemeObj.dot}`,
          }}
        />
        <Palette size={14} style={{ color: activeThemeObj.dot }} />
        <span>{language === 'te' ? activeThemeObj.nameTe.split(' ')[0] : activeThemeObj.nameEn.split(' ')[0]}</span>
      </button>

      {open && (
        <>
          <div
            onClick={() => setOpen(false)}
            style={{ position: 'fixed', inset: 0, zIndex: 110, cursor: 'default' }}
          />
          <div
            className="theme-switcher-menu"
            style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              right: 0,
              zIndex: 120,
              width: '240px',
              background: '#0c1824',
              border: `1px solid ${activeThemeObj.dot}66`,
              borderRadius: '14px',
              padding: '8px',
              boxShadow: `0 20px 50px rgba(0, 0, 0, 0.8), 0 0 20px ${activeThemeObj.dot}26`,
              backdropFilter: 'blur(16px)',
            }}
          >
            <div
              style={{
                fontSize: '10px',
                fontWeight: 800,
                letterSpacing: '0.1em',
                color: '#8fa998',
                padding: '6px 10px',
                textTransform: 'uppercase',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span>{language === 'te' ? 'రంగుల థీమ్ ప్రయోగం' : 'Color Experiment'}</span>
              {currentTheme !== 'emerald' && (
                <button
                  onClick={() => applyTheme('emerald')}
                  title="Reset to default"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: activeThemeObj.dot,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '10px',
                    fontWeight: 700,
                    padding: 0,
                  }}
                >
                  <RotateCcw size={10} /> {language === 'te' ? 'రీసెట్' : 'Reset'}
                </button>
              )}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '4px' }}>
              {THEMES.map(t => {
                const isSelected = t.id === currentTheme
                return (
                  <button
                    key={t.id}
                    onClick={() => applyTheme(t.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '8px 12px',
                      borderRadius: '9px',
                      background: isSelected ? `${t.dot}29` : 'transparent',
                      border: isSelected ? `1px solid ${t.dot}` : '1px solid transparent',
                      color: isSelected ? '#ffffff' : '#d1e5d7',
                      fontSize: '12px',
                      fontWeight: isSelected ? 700 : 500,
                      cursor: 'pointer',
                      textAlign: 'left',
                      width: '100%',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <span
                      style={{
                        width: '12px',
                        height: '12px',
                        borderRadius: '50%',
                        background: t.dot,
                        boxShadow: isSelected ? `0 0 10px ${t.dot}` : 'none',
                        flexShrink: 0,
                      }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {language === 'te' ? t.nameTe : t.nameEn}
                      </span>
                    </div>
                    {isSelected && <Check size={14} style={{ color: t.dot }} />}
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
