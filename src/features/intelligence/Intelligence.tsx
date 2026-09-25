import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Activity, CloudSun, FlaskConical, MapPin, Sprout, TrendingUp } from 'lucide-react'
import { api } from '../../lib/api'
import { PageHeader, Panel } from '../../components/UI'

const tools = [
  { title: 'Crop health', text: 'Image and symptom analysis with source-labelled fallback.', to: '/report', icon: Activity },
  { title: 'Weather intelligence', text: 'Observed field conditions, forecast, and cache status.', to: '/weather', icon: CloudSun },
  { title: 'Nearby activity', text: 'Coarse clusters from recent related reports.', to: '/alerts', icon: MapPin },
  { title: 'Market intelligence', text: 'Mandi quotes, trends, comparisons, and return estimates.', to: '/market', icon: TrendingUp },
  { title: 'Seed planning', text: 'Crop suitability from your saved farm and soil context.', to: '/recommendations', icon: Sprout },
  { title: 'Nutrient guidance', text: 'Conservative soil nutrient observations without dose claims.', to: '/recommendations', icon: FlaskConical },
]

export default function Intelligence() {
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, retry: false })
  const capabilities = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities, retry: false })
  return <div className="page"><PageHeader eyebrow="AGRIVISION / INTELLIGENCE CENTER" title="Connected field intelligence" description="Specialized services combine observations, weather, nearby activity, market context, and soil records."/><div className="planning-hero intelligence-hero"><div className="planning-glow"/><span className="eyebrow">ONE FARM / MULTIPLE SIGNALS</span><h2>Every signal in<br/><em>one clear picture.</em></h2><p>Each result shows where its data came from and when a live provider was unavailable.</p><div className="p4-intelligence-status"><span className={`source-badge source-${health.data?.demo_mode ? 'demo' : health.isError ? 'fallback' : 'live'}`}>{health.data?.demo_mode ? 'LOCAL DEMO WORKSPACE' : health.isError ? 'API UNAVAILABLE' : 'CONNECTED'}</span><span>{capabilities.data ? `${Object.keys(capabilities.data.capabilities).length} connected capabilities` : 'Capabilities loading'}</span></div></div><div className="intelligence-grid">{tools.map(item => { const Icon = item.icon; return <Link to={item.to} key={item.title} className="p4-intelligence-link"><Panel className="intelligence-card"><span className="detail-icon mint"><Icon size={21}/></span><h3>{item.title}</h3><p>{item.text}</p><small>Open workspace →</small></Panel></Link> })}</div>{capabilities.isError && <p className="form-error" role="alert">Capabilities could not be loaded. Reconnect to use the intelligence services.</p>}</div>
}
