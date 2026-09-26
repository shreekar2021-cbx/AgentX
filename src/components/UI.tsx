import type { ReactNode } from 'react'
import { ArrowUpRight, Database, Radio, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { SourceStatus } from '../lib/types'
import { Card3D } from './Card3D'

export function SourceBadge({ status = 'DEMO' }: { status?: SourceStatus }) {
  const isLive = status === 'LIVE'
  return (
    <span className={`source-badge source-${status.toLowerCase()}`}>
      {isLive ? <Radio size={11} className="source-live-pulsar" /> : status === 'DEMO' ? <Sparkles size={11} /> : <Database size={11} />}
      {status} DATA
    </span>
  )
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <div className="eyebrow">{children}</div>
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="page-action">{action}</div>}
    </div>
  )
}

export function Panel({
  children,
  className = '',
  tilt = false,
  glare = true,
  style,
}: {
  children: ReactNode
  className?: string
  tilt?: boolean
  glare?: boolean
  style?: React.CSSProperties
}) {
  if (tilt) {
    return (
      <Card3D className={`panel ${className}`} glare={glare} intensity={10} style={style}>
        {children}
      </Card3D>
    )
  }
  return <section className={`panel ${className}`} style={style}>{children}</section>
}

export function SectionHead({ title, to, label = 'View all', aside }: { title: string; to?: string; label?: string; aside?: ReactNode }) {
  return (
    <div className="section-head">
      <h2>{title}</h2>
      <div>
        {aside}
        {to && (
          <Link className="subtle-link" to={to}>
            {label}
            <ArrowUpRight size={15} />
          </Link>
        )}
      </div>
    </div>
  )
}

export function Stat({
  label,
  value,
  change,
  icon,
  glow = false,
}: {
  label: string
  value: string
  change?: string
  icon?: ReactNode
  glow?: boolean
}) {
  return (
    <Card3D intensity={14} glare={true} className={`stat stat-3d ${glow ? 'stat-glow' : ''}`}>
      <div className="stat-top">
        <span>{label}</span>
        <div className="stat-icon-wrapper">{icon}</div>
      </div>
      <strong>{value}</strong>
      {change && <small>{change}</small>}
    </Card3D>
  )
}

export function SeverityBadge({
  severity,
  label,
}: {
  severity: 'Low' | 'Moderate' | 'High'
  label?: string
}) {
  const sevKey = severity.toLowerCase()
  return (
    <span className={`severity severity-${sevKey} severity-3d`}>
      <i className="severity-dot" />
      {label ?? severity}
    </span>
  )
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <div className="empty-orbit">
        <Sparkles size={24} />
      </div>
      <h3>{title}</h3>
      <p>{body}</p>
      {action}
    </div>
  )
}

export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-label="Loading" />
}

export function AudioWaveVisualizer({ active = false }: { active?: boolean }) {
  return (
    <div className={`audio-wave-bars ${active ? 'is-active' : ''}`} aria-hidden="true">
      <span className="wave-bar bar-1" />
      <span className="wave-bar bar-2" />
      <span className="wave-bar bar-3" />
      <span className="wave-bar bar-4" />
      <span className="wave-bar bar-5" />
    </div>
  )
}
