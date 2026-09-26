import { lazy, Suspense, useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Activity, Bell, ChevronDown, ChevronRight, CircleHelp, CloudSun, LayoutDashboard, Leaf, MapPin, Menu, PanelLeftClose, PanelLeftOpen, Plus, Search, Settings, ShieldCheck, Sprout, TrendingUp, WandSparkles, X } from 'lucide-react'
import { api } from './lib/api'
import { useTranslation, type TranslationKey } from './lib/i18n'
import { useQueueStatus } from './lib/useQueueStatus'
import { useUI } from './lib/store'
import { Skeleton } from './components/UI'
import MyReports from './features/reports/MyReports'
import VoiceAssistant from './components/VoiceAssistant'

const Home = lazy(() => import('./features/home/Home'))
const Intelligence = lazy(() => import('./features/intelligence/Intelligence'))
const SettingsPage = lazy(() => import('./features/settings/Settings'))
const ReportProblem = lazy(() => import('./features/reports/ReportProblem'))
const CropResult = lazy(() => import('./features/reports/CropResult'))
const NearbyAlerts = lazy(() => import('./features/alerts/NearbyAlerts'))
const Weather = lazy(() => import('./features/weather/Weather'))
const Market = lazy(() => import('./features/market/Market'))
const FarmProfile = lazy(() => import('./features/farm/FarmProfile'))
const MyCrops = lazy(() => import('./features/farm/MyCrops'))
const Recommendations = lazy(() => import('./features/recommendations/Recommendations'))
const Notifications = lazy(() => import('./features/notifications/Notifications'))
const ProviderHealth = lazy(() => import('./features/admin/ProviderHealth'))

const nav: { labelKey: TranslationKey; links: { to: string; key: TranslationKey; icon: typeof Leaf }[] }[] = [
  { labelKey: 'navOverview', links: [{ to: '/', key: 'home', icon: LayoutDashboard }, { to: '/intelligence', key: 'intelligence', icon: WandSparkles }, { to: '/report', key: 'report', icon: Plus }] },
  { labelKey: 'navYourFarm', links: [{ to: '/crops', key: 'crops', icon: Sprout }, { to: '/alerts', key: 'alerts', icon: MapPin }, { to: '/reports', key: 'reports', icon: Activity }, { to: '/weather', key: 'weather', icon: CloudSun }] },
  { labelKey: 'navExplore', links: [{ to: '/market', key: 'market', icon: TrendingUp }, { to: '/recommendations', key: 'recommendations', icon: Leaf }, { to: '/admin', key: 'admin', icon: ShieldCheck }] },
]
const flatNav = nav.flatMap(group => group.links)

function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, mobileMenuOpen, setMobileMenuOpen } = useUI()
  const { t } = useTranslation()
  const profile = useQuery({ queryKey: ['farm-profile'], queryFn: api.farmProfile })
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, retry: false })
  return <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''} ${mobileMenuOpen ? 'mobile-open' : ''}`}>
    <div className="brand"><span className="brand-mark"><Leaf size={23} strokeWidth={2.2}/></span><span className="brand-name">AgriVision<span>AI</span><small>{t('fieldIntelligence')}</small></span></div>
    <button className="sidebar-toggle" onClick={() => window.innerWidth < 701 ? setMobileMenuOpen(false) : toggleSidebar()} title={sidebarCollapsed ? t('expandNav') : t('collapseNav')}>{sidebarCollapsed ? <PanelLeftOpen size={18}/> : <PanelLeftClose size={18}/>}</button>
    <NavLink to="/farm" className="farm-select"><div className="farm-symbol"><Sprout size={18}/></div><div><strong>{profile.data?.farm_name || t('yourFarm')}</strong><small>{profile.data?.district || t('completeProfile')}</small></div><ChevronDown size={14}/></NavLink>
    <nav aria-label="Main navigation" onClick={() => setMobileMenuOpen(false)}>{nav.map(group => <div className="nav-group" key={group.labelKey}><span className="nav-heading">{t(group.labelKey)}</span>{group.links.map(({ to, key, icon: Icon }) => <NavLink key={to} end={to === '/'} to={to} title={t(key)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Icon size={19} strokeWidth={1.8}/><span>{t(key)}</span></NavLink>)}</div>)}</nav>
    <div className="sidebar-bottom"><div className="sidebar-help"><span className="help-icon"><CircleHelp size={18}/></span><strong>{t('needGuidance')}</strong><p>{t('sidebarHelpText')}</p><NavLink to="/intelligence">{t('explorePlatform')} <ChevronRight size={14}/></NavLink></div><NavLink to="/settings" className="nav-link"><Settings size={18}/><span>{t('settings')}</span></NavLink><div className="sidebar-profile"><div className="avatar"><Leaf size={17}/></div><span><strong>{health.data?.demo_mode ? t('demoWorkspace') : t('farmWorkspace')}</strong><small>{health.data?.demo_mode ? t('syntheticRecords') : t('authRequired')}</small></span><ChevronDown size={14}/></div></div>
  </aside>
}

function SearchOverlay() {
  const { searchOpen, setSearchOpen } = useUI()
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  useEffect(() => { const listener = (event: KeyboardEvent) => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setSearchOpen(true) } if (event.key === 'Escape') setSearchOpen(false) }; window.addEventListener('keydown', listener); return () => window.removeEventListener('keydown', listener) }, [setSearchOpen])
  if (!searchOpen) return null
  const results = flatNav.filter(item => t(item.key).toLowerCase().includes(query.toLowerCase()))
  return <div className="search-backdrop" onClick={() => setSearchOpen(false)}><div className="search-modal" onClick={event => event.stopPropagation()}><div className="search-input"><Search size={20}/><input autoFocus placeholder={t('searchPlaceholder')} value={query} onChange={event => setQuery(event.target.value)}/><button onClick={() => setSearchOpen(false)}><X size={18}/></button></div><div className="search-results"><small>{t('quickNavigation')}</small>{results.length ? results.map(item => <button key={item.to} onClick={() => { navigate(item.to); setSearchOpen(false); setQuery('') }}><item.icon size={18}/>{t(item.key)}<ChevronRight size={16}/></button>) : <p>{t('noMatchingPages')}</p>}</div></div></div>
}

function Topbar() {
  const location = useLocation()
  const { setSearchOpen, language, setLanguage } = useUI()
  const { t } = useTranslation()
  const queue = useQueueStatus()
  const navItem = flatNav.find(item => item.to === location.pathname)
  const title = navItem ? t(navItem.key) : location.pathname.startsWith('/result') ? t('cropResult') : t('farm')
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, retry: false, refetchInterval: 60_000 })
  const notifications = useQuery({ queryKey: ['notifications'], queryFn: api.notifications, retry: false, refetchInterval: 30_000 })
  const unread = notifications.data?.filter(item => !item.read_at).length ?? 0
  return <header className="topbar"><div className="breadcrumb"><span>{t('workspace')}</span><ChevronRight size={14}/><strong>{title}</strong></div><div className="topbar-actions"><span className={`p3-online ${queue.online ? 'is-online' : 'is-offline'}`} role="status">{queue.online ? t('online') : t('offline')}{queue.count > 0 ? ` · ${queue.count}` : ''}</span>{health.isPending ? <Skeleton className="health-skeleton"/> : <span className="api-status" title={health.isSuccess ? t('backendConnected') : t('backendUnavailable')}><i className={health.isSuccess ? 'online' : ''}/>{health.isSuccess ? t('systemConnected') : t('serviceUnavailable')}</span>}<label className="p3-language">{t('language')}<select aria-label={t('language')} value={language} onChange={event => setLanguage(event.target.value as 'en' | 'te' | 'hi')}><option value="en">{t('langEnglish')}</option><option value="te">{t('langTelugu')}</option><option value="hi">{t('langHindi')}</option></select></label><button className="search-trigger" onClick={() => setSearchOpen(true)}><Search size={17}/><span>{t('searchAnything')}</span><kbd>Ctrl K</kbd></button><NavLink className="icon-button" to="/notifications" aria-label={t('notifications')}><Bell size={19}/>{unread > 0 && <b className="p3-unread">{unread}</b>}</NavLink><NavLink className="top-avatar" to="/farm" aria-label={t('farm')}>RK</NavLink></div></header>
}

function MobileNav() { const { t } = useTranslation(); return <nav className="mobile-nav" aria-label="Mobile navigation"><NavLink to="/" end><LayoutDashboard size={21}/><span>{t('home')}</span></NavLink><NavLink to="/crops"><Sprout size={21}/><span>{t('crops')}</span></NavLink><NavLink className="mobile-scan" to="/report"><Plus size={25}/><span>{t('report')}</span></NavLink><NavLink to="/alerts"><MapPin size={21}/><span>{t('alerts')}</span></NavLink><NavLink to="/market"><TrendingUp size={21}/><span>{t('market')}</span></NavLink></nav> }

export default function App() {
  const { sidebarCollapsed, mobileMenuOpen, setMobileMenuOpen, language } = useUI()
  useEffect(() => { document.documentElement.lang = language }, [language])
  return <div className={`app-shell ${sidebarCollapsed ? 'is-collapsed' : ''}`}><Sidebar/><div className="mobile-top"><button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} aria-label="Toggle navigation"><Menu size={21}/></button><span className="mobile-brand"><Leaf size={19}/> AgriVision <b>AI</b></span><NavLink to="/notifications"><Bell size={20}/></NavLink></div><div className="main-wrap"><Topbar/><main className="content"><Suspense fallback={<Skeleton className="result-loading"/>}><Routes><Route path="/" element={<Home/>}/><Route path="/report" element={<ReportProblem/>}/><Route path="/result/:id" element={<CropResult/>}/><Route path="/crops" element={<MyCrops/>}/><Route path="/alerts" element={<NearbyAlerts/>}/><Route path="/reports" element={<MyReports/>}/><Route path="/market" element={<Market/>}/><Route path="/recommendations" element={<Recommendations/>}/><Route path="/admin" element={<ProviderHealth/>}/><Route path="/farm" element={<FarmProfile/>}/><Route path="/notifications" element={<Notifications/>}/><Route path="/settings" element={<SettingsPage/>}/><Route path="/weather" element={<Weather/>}/><Route path="/intelligence" element={<Intelligence/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></Suspense></main><footer className="footer"><span>© 2026 AgriVision AI · Field intelligence · Check source labels</span><span className="source-badge source-cached">SOURCE LABELS PER SCREEN</span></footer></div><MobileNav/><SearchOverlay/><VoiceAssistant/><div className={`mobile-sidebar-dismiss ${mobileMenuOpen ? 'open' : ''}`} onClick={() => setMobileMenuOpen(false)}/></div>
}
