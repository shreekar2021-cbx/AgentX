import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Activity, Bell, ChevronDown, CircleHelp, CloudSun, Command, LayoutDashboard, Leaf, Menu, Search, ShieldCheck, Sprout, TrendingUp, X } from 'lucide-react'
import { Avatar } from '../ui'
import { farmer } from '../../data/mockData'
import { useAppStore } from '../../store/useAppStore'

const navSections = [
  { label: 'WORKSPACE', links: [
    { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
    { to: '/report', label: 'Report a problem', icon: CircleHelp },
    { to: '/crops', label: 'My crops', icon: Sprout },
    { to: '/alerts', label: 'Nearby alerts', icon: Activity, badge: '2' },
    { to: '/reports', label: 'My reports', icon: Leaf },
  ] },
  { label: 'INSIGHTS', links: [
    { to: '/market', label: 'Market prices', icon: TrendingUp },
    { to: '/farm', label: 'Seed & soil', icon: CloudSun },
  ] },
]

const titles = { '/': 'Overview', '/report': 'Report a problem', '/crops': 'My crops', '/alerts': 'Nearby alerts', '/reports': 'My reports', '/market': 'Market intelligence', '/farm': 'Seed & fertilizer', '/admin': 'Admin dashboard' }

export default function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const language = useAppStore((state) => state.language)
  const setLanguage = useAppStore((state) => state.setLanguage)
  const notificationsOpen = useAppStore((state) => state.notificationsOpen)
  const toggleNotifications = useAppStore((state) => state.toggleNotifications)
  const location = useLocation()
  const title = location.pathname.startsWith('/reports/') ? 'Crop result' : titles[location.pathname] || 'AgriVision'
  const mobileLinks = [
    { to: '/', label: 'Home', icon: LayoutDashboard, end: true },
    { to: '/report', label: 'Report', icon: CircleHelp },
    { to: '/alerts', label: 'Alerts', icon: Activity },
    { to: '/market', label: 'Market', icon: TrendingUp },
    { to: '/crops', label: 'My farm', icon: Sprout },
  ]
  const linkClass = ({ isActive }) => `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-semibold transition ${isActive ? 'bg-leaf-50 text-leaf-700' : 'text-[#738177] hover:bg-[#f6f8f4] hover:text-ink'}`
  const SidebarContent = () => <>
    <NavLink to="/" className="mb-9 flex items-center gap-3 px-2 pt-1" onClick={() => setMobileOpen(false)}><span className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-ink text-lime"><Sprout size={23} strokeWidth={2.3} /></span><span><span className="block text-[15px] font-extrabold tracking-tight text-ink">agri<span className="text-leaf-600">vision</span></span><span className="mt-0.5 block text-[9px] font-bold uppercase tracking-[.19em] text-muted">Farm intelligence</span></span></NavLink>
    {navSections.map((section) => <div className="mb-7" key={section.label}><p className="mb-2 px-3 text-[9px] font-extrabold tracking-[.17em] text-[#a4aea5]">{section.label}</p><div className="space-y-1">{section.links.map((item) => <NavLink key={item.to} to={item.to} end={item.end} className={linkClass} onClick={() => setMobileOpen(false)}><item.icon size={17} strokeWidth={1.9} /><span className="flex-1">{item.label}</span>{item.badge && <span className="rounded-md bg-white px-1.5 py-0.5 text-[10px] font-bold text-leaf-700 shadow-sm">{item.badge}</span>}</NavLink>)}</div></div>)}
    <div className="mb-7"><p className="mb-2 px-3 text-[9px] font-extrabold tracking-[.17em] text-[#a4aea5]">MANAGEMENT</p><NavLink to="/admin" className={linkClass} onClick={() => setMobileOpen(false)}><ShieldCheck size={17} /><span>Admin dashboard</span></NavLink></div>
    <div className="mt-auto rounded-2xl bg-[#f3f6ee] p-4"><div className="mb-2 flex items-center gap-2"><CloudSun size={16} className="text-leaf-700" /><span className="text-xs font-bold text-ink">A good day to grow</span></div><p className="text-[11px] leading-5 text-muted">Light rain expected Thursday. Keep an eye on your tomato crop.</p><div className="mt-3 flex items-center justify-between text-[10px] font-semibold text-[#839087]"><span>Warangal · 31°C</span><span>Partly cloudy</span></div></div>
    <div className="mt-5 flex items-center gap-3 border-t border-[#edf0ea] pt-4"><Avatar initials={farmer.avatar} /><div className="min-w-0 flex-1"><p className="truncate text-xs font-bold text-ink">{farmer.name}</p><p className="mt-0.5 truncate text-[10px] text-muted">{farmer.location}</p></div><ChevronDown size={15} className="text-muted" /></div>
  </>

  return <div className="min-h-screen bg-canvas lg:flex">
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col border-r border-[#e9eee5] bg-white px-5 py-6 lg:flex"><SidebarContent /></aside>
    {mobileOpen && <div className="fixed inset-0 z-50 lg:hidden"><button aria-label="Close navigation" className="absolute inset-0 bg-ink/30" onClick={() => setMobileOpen(false)} /><aside className="absolute inset-y-0 left-0 flex w-[280px] flex-col bg-white px-5 py-6 shadow-xl"><div className="mb-4 flex justify-end"><button onClick={() => setMobileOpen(false)}><X size={20} /></button></div><SidebarContent /></aside></div>}
    <main className="min-h-screen min-w-0 flex-1 lg:ml-[248px]">
      <header className="sticky top-0 z-20 flex h-[72px] items-center justify-between border-b border-[#e9eee5]/80 bg-canvas/90 px-4 backdrop-blur-xl sm:px-7 lg:px-10">
        <div className="flex items-center gap-3"><button className="rounded-lg p-2 text-ink hover:bg-white lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><div><p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#98a59b]">FARMER WORKSPACE</p><p className="mt-0.5 text-[13px] font-bold text-ink">{title}</p></div></div>
        <div className="flex items-center gap-2 sm:gap-3"><span className="hidden rounded-full border border-[#e5eae1] bg-white px-2.5 py-1.5 text-[9px] font-bold uppercase tracking-wider text-amber-700 md:inline-flex">Mock data</span><button onClick={() => setLanguage(language === 'en' ? 'te' : 'en')} className="rounded-lg border border-[#e5eae1] bg-white px-2 py-2 text-[10px] font-extrabold text-ink" aria-label="Switch interface language">{language === 'en' ? 'EN' : 'తె'}</button><button className="hidden items-center gap-2 rounded-xl border border-[#e5eae1] bg-white px-3 py-2 text-xs text-[#9aa59d] sm:flex"><Search size={14} /><span>Search anything...</span><kbd className="ml-5 rounded border border-[#e8ece5] px-1.5 py-0.5 text-[9px]">⌘ K</kbd></button><div className="relative"><button onClick={toggleNotifications} className="relative rounded-xl border border-[#e5eae1] bg-white p-2.5 text-muted hover:text-ink" aria-label="Notifications" aria-expanded={notificationsOpen}><Bell size={17} /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-amber-500 ring-2 ring-white" /></button>{notificationsOpen && <div className="absolute right-0 top-12 z-40 w-[min(320px,calc(100vw-32px))] rounded-2xl border border-[#e8ece5] bg-white p-4 shadow-card"><div className="mb-3 flex items-center justify-between"><p className="text-xs font-extrabold text-ink">Notifications</p><span className="rounded-full bg-amber-50 px-2 py-1 text-[9px] font-bold text-amber-700">2 new</span></div><p className="border-b border-[#eff2ec] py-2.5 text-[11px] leading-5 text-muted"><b className="text-ink">Tomato alert nearby</b><br />Early blight activity reported near Hanamkonda.</p><p className="py-2.5 text-[11px] leading-5 text-muted"><b className="text-ink">Market update</b><br />Enumamula tomato prices moved up this week.</p><p className="mt-1 text-[9px] text-[#98a59b]">Mock notifications · not live updates</p></div>}</div><div className="hidden h-7 w-px bg-[#e3e8df] sm:block" /><div className="hidden items-center gap-2 rounded-full bg-white px-2 py-1.5 sm:flex"><span className="rounded-full bg-[#f1f4ed] p-1.5"><Command size={13} className="text-leaf-700" /></span><span className="text-[11px] font-bold text-ink">Farmer</span></div><span className="hidden text-muted sm:block"><ChevronDown size={14} /></span></div>
      </header>
      <div className="mx-auto max-w-[1440px] px-4 pb-28 pt-7 sm:px-7 lg:px-10 lg:pb-10 lg:pt-9"><Outlet /></div>
    </main>
    <nav aria-label="Farmer navigation" className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 border-t border-[#e9eee5] bg-white/95 px-2 pb-[max(env(safe-area-inset-bottom),8px)] pt-2 backdrop-blur-lg lg:hidden">{mobileLinks.map((item) => <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `flex flex-col items-center gap-1 rounded-xl py-1.5 text-[9px] font-bold ${isActive ? 'text-leaf-700' : 'text-[#8d9990]'}`}><item.icon size={19} strokeWidth={2} /><span>{item.label}</span></NavLink>)}</nav>
  </div>
}
