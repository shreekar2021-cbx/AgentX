import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Activity, CloudSun, FlaskConical, MapPin, Sprout, TrendingUp } from 'lucide-react'
import { api } from '../../lib/api'
import { PageHeader, Panel } from '../../components/UI'
import { useTranslation } from '../../lib/i18n'

export default function Intelligence() {
  const { t } = useTranslation()
  const tools = [
    { title: t('cropHealthTool'), text: t('cropHealthDesc'), to: '/report', icon: Activity },
    { title: t('weatherIntelligence'), text: t('weatherIntelDesc'), to: '/weather', icon: CloudSun },
    { title: t('nearbyActivity'), text: t('nearbyDesc'), to: '/alerts', icon: MapPin },
    { title: t('marketIntelligenceTool'), text: t('marketIntelDesc'), to: '/market', icon: TrendingUp },
    { title: t('seedPlanning'), text: t('seedPlanDesc'), to: '/recommendations', icon: Sprout },
    { title: t('nutrientGuidance'), text: t('nutrientDesc'), to: '/recommendations', icon: FlaskConical },
  ]
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, retry: false })
  const capabilities = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities, retry: false })
  return <div className="page"><PageHeader eyebrow="AGRIVISION / INTELLIGENCE CENTER" title={t('connectedFieldIntelligence')} description={t('intelligenceDescription')}/><div className="planning-hero intelligence-hero"><div className="planning-glow"/><span className="eyebrow">{t('oneSignal')}</span><h2>{t('everySignalTitle')}<br/><em>{t('oneClearPicture')}</em></h2><p>{t('intelligenceSubtext')}</p><div className="p4-intelligence-status"><span className={`source-badge source-${health.data?.demo_mode ? 'demo' : health.isError ? 'fallback' : 'live'}`}>{health.data?.demo_mode ? 'LOCAL DEMO WORKSPACE' : health.isError ? 'API UNAVAILABLE' : 'CONNECTED'}</span><span>{capabilities.data ? `${Object.keys(capabilities.data.capabilities).length} ${t('connectedCapabilities')}` : t('capabilitiesLoading')}</span></div></div><div className="intelligence-grid">{tools.map(item => { const Icon = item.icon; return <Link to={item.to} key={item.title} className="p4-intelligence-link"><Panel className="intelligence-card"><span className="detail-icon mint"><Icon size={21}/></span><h3>{item.title}</h3><p>{item.text}</p><small>{t('openWorkspace')}</small></Panel></Link> })}</div>{capabilities.isError && <p className="form-error" role="alert">{t('capabilitiesError')}</p>}</div>
}
