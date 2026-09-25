import type { ReactNode } from 'react'
import { ArrowUpRight, Database, Radio, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { SourceStatus } from '../lib/types'

export function SourceBadge({ status = 'DEMO' }: { status?: SourceStatus }) { return <span className={`source-badge source-${status.toLowerCase()}`}>{status === 'LIVE' ? <Radio size={11} /> : status === 'DEMO' ? <Sparkles size={11} /> : <Database size={11} />}{status} DATA</span> }
export function Eyebrow({ children }: { children: ReactNode }) { return <div className="eyebrow">{children}</div> }
export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) { return <div className="page-header"><div><Eyebrow>{eyebrow}</Eyebrow><h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="page-action">{action}</div>}</div> }
export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) { return <section className={`panel ${className}`}>{children}</section> }
export function SectionHead({ title, to, label = 'View all', aside }: { title: string; to?: string; label?: string; aside?: ReactNode }) { return <div className="section-head"><h2>{title}</h2><div>{aside}{to && <Link className="subtle-link" to={to}>{label}<ArrowUpRight size={15} /></Link>}</div></div> }
export function Stat({ label, value, change, icon }: { label: string; value: string; change?: string; icon?: ReactNode }) { return <Panel className="stat"><div className="stat-top"><span>{label}</span>{icon}</div><strong>{value}</strong>{change && <small>{change}</small>}</Panel> }
export function SeverityBadge({ severity }: { severity: 'Low' | 'Moderate' | 'High' }) { return <span className={`severity severity-${severity.toLowerCase()}`}><i />{severity}</span> }
export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) { return <div className="empty-state"><div className="empty-orbit"><Sparkles size={24} /></div><h3>{title}</h3><p>{body}</p>{action}</div> }
export function Skeleton({ className = '' }: { className?: string }) { return <div className={`skeleton ${className}`} aria-label="Loading" /> }
