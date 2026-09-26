import { Card3D } from './Card3D'

interface RiskMeter3DProps {
  score: number
  title?: string
  subtitle?: string
  language?: string
}

export function RiskMeter3D({ score, title = 'Crop Risk Index', subtitle, language = 'en' }: RiskMeter3DProps) {
  const safeScore = Math.max(0, Math.min(100, Math.round(score)))

  // Determine tier & color
  let color = '#34d399' // green
  let glowColor = 'rgba(52, 211, 153, 0.4)'
  let statusText = language === 'te' ? 'సురక్షితం' : 'Safe / Low Risk'

  if (safeScore >= 70) {
    color = '#f87171' // red
    glowColor = 'rgba(248, 113, 113, 0.5)'
    statusText = language === 'te' ? 'తీవ్రమైన ప్రమాదం' : 'Critical Outbreak Risk'
  } else if (safeScore >= 35) {
    color = '#fbbf24' // amber
    glowColor = 'rgba(251, 191, 36, 0.45)'
    statusText = language === 'te' ? 'మధ్యస్థం / అప్రమత్తత' : 'Moderate Attention'
  }

  // Calculate arc geometry for 180-degree gauge
  const radius = 64
  const strokeWidth = 10
  const center = 80
  const circumference = Math.PI * radius
  const strokeDashoffset = circumference - (safeScore / 100) * circumference

  return (
    <Card3D intensity={12} className="risk-meter-3d-card" style={{ padding: '20px', borderRadius: '16px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
        <span style={{ fontSize: '11px', letterSpacing: '0.12em', fontWeight: 700, color: '#8fa99a', textTransform: 'uppercase', marginBottom: '8px' }}>
          {title}
        </span>

        <div style={{ position: 'relative', width: '160px', height: '100px', display: 'flex', justifyContent: 'center' }}>
          <svg width="160" height="96" viewBox="0 0 160 96">
            <defs>
              <linearGradient id="riskTrackGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#1e3a2d" />
                <stop offset="50%" stopColor="#3d3522" />
                <stop offset="100%" stopColor="#3d1e1c" />
              </linearGradient>
              <filter id="gaugeGlow">
                <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor={color} floodOpacity="0.6" />
              </filter>
            </defs>

            {/* Background Arc */}
            <path
              d={`M ${center - radius} ${center} A ${radius} ${radius} 0 0 1 ${center + radius} ${center}`}
              fill="none"
              stroke="#1a2e26"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />

            {/* Colored Metric Arc */}
            <path
              d={`M ${center - radius} ${center} A ${radius} ${radius} 0 0 1 ${center + radius} ${center}`}
              fill="none"
              stroke={color}
              strokeWidth={strokeWidth}
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              filter="url(#gaugeGlow)"
              style={{ transition: 'stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.4s ease' }}
            />
          </svg>

          {/* Center Value */}
          <div
            style={{
              position: 'absolute',
              bottom: '4px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <strong
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontSize: '34px',
                fontWeight: 700,
                color: '#ffffff',
                textShadow: `0 0 16px ${glowColor}`,
                lineHeight: 1,
              }}
            >
              {safeScore}
              <small style={{ fontSize: '14px', color: '#8fa99a', fontWeight: 500 }}>/100</small>
            </strong>
          </div>
        </div>

        {/* Status Pill Badge */}
        <div
          style={{
            marginTop: '10px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: `color-mix(in srgb, ${color} 15%, #0f2119)`,
            border: `1px solid color-mix(in srgb, ${color} 40%, transparent)`,
            color,
            borderRadius: '20px',
            padding: '4px 14px',
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.04em',
            boxShadow: `0 0 12px color-mix(in srgb, ${color} 25%, transparent)`,
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}` }} />
          {statusText}
        </div>

        {subtitle && (
          <p style={{ fontSize: '11px', color: '#8ba395', margin: '10px 0 0', lineHeight: 1.4 }}>
            {subtitle}
          </p>
        )}
      </div>
    </Card3D>
  )
}
