import { ArrowDownRight, ArrowUpRight, ChevronRight, Leaf } from 'lucide-react'
import { Link } from 'react-router-dom'

export function PageHeading({ eyebrow, title, description, action }) {
  return <div className="mb-7 flex flex-wrap items-end justify-between gap-4"><div><p className="mb-2 text-xs font-bold uppercase tracking-[.17em] text-leaf-600">{eyebrow}</p><h1 className="display text-3xl font-extrabold tracking-tight text-ink sm:text-[34px]">{title}</h1>{description && <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p>}</div>{action}</div>
}

export function Card({ children, className = '' }) { return <section className={`rounded-2xl border border-[#e9eee5] bg-white p-5 shadow-card sm:p-6 ${className}`}>{children}</section> }
export function SectionTitle({ children, action, className = '' }) { return <div className={`mb-5 flex items-center justify-between gap-3 ${className}`}><h2 className="text-base font-bold text-ink">{children}</h2>{action}</div> }
export function Pill({ children, tone = 'green' }) {
  const tones = { green: 'bg-leaf-50 text-leaf-700', amber: 'bg-amber-50 text-amber-700', red: 'bg-red-50 text-red-700', gray: 'bg-slate-100 text-slate-600', blue: 'bg-sky-50 text-sky-700' }
  return <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold ${tones[tone]}`}>{children}</span>
}
export function Button({ children, variant = 'primary', className = '', ...props }) {
  const variants = { primary: 'bg-ink text-white hover:bg-[#2d493b]', secondary: 'border border-[#dfe8d9] bg-white text-ink hover:bg-leaf-50', soft: 'bg-leaf-50 text-leaf-700 hover:bg-leaf-100', ghost: 'text-muted hover:bg-canvas hover:text-ink' }
  return <button className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold transition ${variants[variant]} ${className}`} {...props}>{children}</button>
}
export function StatCard({ label, value, detail, icon: Icon = Leaf, trend, tone = 'green' }) {
  const colors = { green: 'bg-leaf-50 text-leaf-700', amber: 'bg-amber-50 text-amber-700', blue: 'bg-sky-50 text-sky-700', red: 'bg-red-50 text-red-700' }
  const positive = trend?.startsWith('+')
  return <Card className="p-5"><div className="flex items-start justify-between"><div><p className="text-xs font-semibold text-muted">{label}</p><p className="mt-3 text-[27px] font-extrabold tracking-tight text-ink">{value}</p></div><span className={`rounded-xl p-2.5 ${colors[tone]}`}><Icon size={19} /></span></div><div className="mt-3 flex items-center gap-1.5 text-xs text-muted">{trend && <span className={`flex items-center font-bold ${positive ? 'text-leaf-700' : 'text-red-600'}`}>{positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{trend}</span>}{detail}</div></Card>
}
export function SeeAll({ to, children = 'View all' }) { return <Link to={to} className="inline-flex items-center gap-1 text-xs font-bold text-leaf-700 hover:text-leaf-600">{children}<ChevronRight size={14} /></Link> }
export function ProgressBar({ value, color = 'bg-leaf-500' }) { return <div className="h-2 overflow-hidden rounded-full bg-[#edf1e9]"><div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} /></div> }
export function Avatar({ initials }) { return <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#deebd2] text-xs font-extrabold text-leaf-700">{initials}</div> }
