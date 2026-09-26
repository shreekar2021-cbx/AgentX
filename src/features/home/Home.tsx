import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useReducedMotion, motion } from 'framer-motion'
import { Activity, ArrowRight, CloudSun, Leaf, MapPin, Plus, Sparkles, Sprout, Wind, Droplets } from 'lucide-react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts'
import { api } from '../../lib/api'
import { useQueueStatus } from '../../lib/useQueueStatus'
import { EmptyState, Eyebrow, Panel, SectionHead, Skeleton, Stat } from '../../components/UI'
import { useTranslation } from '../../lib/i18n'
import { Card3D } from '../../components/Card3D'
import { ThreeCropVisual } from '../../components/ThreeCropVisual'

const money = (value: number) => `₹${Math.round(value).toLocaleString('en-IN')}`

export default function Home() {
  const { t, language } = useTranslation()
  const reducedMotion = useReducedMotion()
  const queue = useQueueStatus()
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, retry: false })
  const profile = useQuery({ queryKey: ['farm-profile'], queryFn: api.farmProfile, retry: false })
  const crops = useQuery({ queryKey: ['portfolio'], queryFn: api.portfolio, retry: false })
  const reports = useQuery({ queryKey: ['reports'], queryFn: api.reports, retry: false })
  const coordinates = profile.data?.latitude != null && profile.data.longitude != null ? [profile.data.latitude, profile.data.longitude] as const : null
  const weather = useQuery({ queryKey: ['weather', coordinates], queryFn: () => api.weather(coordinates![0], coordinates![1]), enabled: Boolean(coordinates), retry: false })
  const market = useQuery({ queryKey: ['market-prices', 'Cotton', profile.data?.district], queryFn: () => api.marketPrices('Cotton', profile.data?.district ?? undefined), retry: false })
  const alerts = useQuery({ queryKey: ['nearby-alerts', 'Cotton', coordinates], queryFn: () => api.nearbyAlerts('Cotton', coordinates![0], coordinates![1]), enabled: Boolean(coordinates), retry: false })

  const recent = reports.data?.slice(0, 3) ?? []
  const latestPrice = market.data?.quotes[0]

  return (
    <motion.div
      className="page home-page"
      initial={reducedMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
    >
      <div className="home-heading">
        <div>
          <Eyebrow>{t('fieldIntelligenceOverview')}</Eyebrow>
          <h1>{profile.data?.farm_name ? `${profile.data.farm_name}` : t('fieldOverviewTitle')}</h1>
          <p>{t('overviewSubtitle')}</p>
        </div>
        <Link className="button primary" to="/report" style={{ fontSize: '13px', padding: '10px 20px' }}>
          <Plus size={18} /> {t('reportAProblem')}
        </Link>
      </div>

      {health.data?.demo_mode && (
        <div className="demo-notice" style={{ border: '1px solid rgba(52, 211, 153, 0.35)', background: 'rgba(16, 38, 28, 0.7)' }}>
          <Leaf size={16} />
          <span>{t('demoNotice')}</span>
        </div>
      )}
      {health.isError && (
        <div className="form-error" role="alert">
          {t('apiUnavailable')}
        </div>
      )}

      {/* 3D Elevated Interactive Hero with Three.js Live Bio-Visual */}
      <Card3D intensity={8} glare={true} style={{ margin: '22px 0' }}>
        <div className="hero-3d-container">
          <div className="hero-content">
            <div className="hero-kicker">
              <span className="pulse-dot" />
              <span>{t('cropHealthActionCenter')}</span>
              <span className="source-badge source-live">3D HOLOGRAPHIC VIEW</span>
            </div>
            <h2>
              {t('seeFieldClearly')}
              <br />
              <em>{t('actWithContext')}</em>
            </h2>
            <p>{t('submitCropImage')}</p>
            <div className="hero-actions" style={{ marginTop: '22px' }}>
              <Link className="button primary" to="/report">
                {t('startCropAnalysis')} <ArrowRight size={16} />
              </Link>
              <Link className="button secondary" to="/intelligence">
                {t('exploreIntelligence')}
              </Link>
            </div>
          </div>

          <div className="hero-3d-canvas-wrap">
            <div className="hero-3d-badge">
              <Sparkles size={12} />
              <span>{language === 'te' ? 'ప్రత్యక్ష 3D పంట వీక్షణ' : 'Interactive 3D Field Mesh'}</span>
            </div>
            <ThreeCropVisual status="healthy" height={290} />
          </div>
        </div>
      </Card3D>

      {/* 3D Interactive Metrics Grid */}
      <div className="metrics-grid p4-metrics">
        <Stat
          label={t('cropFields')}
          value={crops.isPending ? '…' : String(crops.data?.length ?? 0).padStart(2, '0')}
          change={crops.isError ? t('unavailable') : t('fromPortfolio')}
          icon={<Sprout size={20} />}
          glow
        />
        <Stat
          label={t('myReportsLabel')}
          value={reports.isPending ? '…' : String(reports.data?.length ?? 0).padStart(2, '0')}
          change={reports.isError ? t('unavailable') : t('storedObservations')}
          icon={<Activity size={20} />}
        />
        <Stat
          label={t('cottonClusters')}
          value={alerts.isPending ? '…' : String(alerts.data?.length ?? 0).padStart(2, '0')}
          change={
            alerts.isError
              ? t('unavailable')
              : alerts.data?.some(item => item.is_synthetic)
              ? t('includesSyntheticDemo')
              : t('nearbyObservations')
          }
          icon={<MapPin size={20} />}
        />
        <Stat
          label={t('waitingToSync')}
          value={String(queue.count).padStart(2, '0')}
          change={queue.online ? t('online') : t('offline')}
          icon={<CloudSun size={20} />}
        />
      </div>

      {/* Weather and Field Signal Card */}
      <div className="p4-home-grid">
        <Card3D intensity={10}>
          <Panel style={{ height: '100%' }}>
            <SectionHead title={t('weatherContext')} to="/weather" />
            <span
              className={`source-badge source-${
                weather.data?.source === 'LIVE' ? 'live' : weather.data?.source === 'CACHED' ? 'cached' : 'fallback'
              }`}
            >
              {weather.data?.source ?? (weather.isError ? t('unavailable') : 'AWAITING DATA')}
            </span>
            {weather.isPending && coordinates ? (
              <Skeleton className="p4-signal-skeleton" />
            ) : weather.data?.current ? (
              <div style={{ marginTop: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '14px' }}>
                  <strong style={{ fontSize: '46px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, color: '#e8fbf1' }}>
                    {Math.round(weather.data.current.temperature_c)}°C
                  </strong>
                  <div style={{ display: 'flex', gap: '16px', color: '#97b8a5', fontSize: '13px' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                      <Droplets size={15} color="#60a5fa" />
                      {weather.data.current.relative_humidity_pct}% {t('humidity').toLowerCase()}
                    </span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
                      <Wind size={15} color="#34d399" />
                      {weather.data.current.precipitation_mm} mm {t('rainfall').toLowerCase()}
                    </span>
                  </div>
                </div>
                <small style={{ color: '#7b9987', display: 'block', marginTop: '10px' }}>
                  {t('observed')} {new Date(weather.data.current.observed_at).toLocaleString('en-IN')}
                </small>
              </div>
            ) : (
              <p>{coordinates ? t('weatherUnavailableMsg') : t('addFarmCoordinates')}</p>
            )}
          </Panel>
        </Card3D>

        {/* Cotton Market Pulse with Area Chart */}
        <Card3D intensity={10}>
          <Panel style={{ height: '100%' }}>
            <SectionHead title={t('cottonMarketPulse')} to="/market" />
            {market.isPending ? (
              <Skeleton className="p4-signal-skeleton" />
            ) : market.isError ? (
              <EmptyState title={t('marketUnavailable')} body={market.error.message} />
            ) : (
              <>
                <div className="p4-market-top" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                  <strong style={{ fontSize: '32px', fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, color: '#86efac' }}>
                    {latestPrice ? money(latestPrice.modal_price) : t('noQuote')}
                  </strong>
                  <span className={`source-badge source-${market.data?.source.toLowerCase()}`}>
                    {market.data?.is_synthetic ? `${t('synthetic')} ` : ''}
                    {market.data?.source}
                  </span>
                </div>
                <small style={{ color: '#7b9987', display: 'block', margin: '4px 0 12px' }}>
                  {t('modalPricePerQuintal')} · {latestPrice?.mandi ?? t('noMandi')}
                </small>
                <div className="p4-mini-chart" role="img" aria-label="Cotton modal price history" style={{ height: '110px' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={market.data?.history_30d ?? []}>
                      <defs>
                        <linearGradient id="marketGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#34d399" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="date" hide />
                      <Tooltip formatter={value => money(Number(value))} />
                      <Area dataKey="modal_price" type="monotone" stroke="#34d399" fill="url(#marketGrad)" strokeWidth={2.5} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </Panel>
        </Card3D>
      </div>

      {/* Reports and Alerts */}
      <div className="p4-home-grid" style={{ marginTop: '18px' }}>
        <Card3D intensity={8}>
          <Panel style={{ height: '100%' }}>
            <SectionHead title={t('recentFieldReports')} to="/reports" />
            {reports.isPending ? (
              <Skeleton className="p4-signal-skeleton" />
            ) : reports.isError ? (
              <EmptyState title={t('reportsUnavailable')} body={reports.error.message} />
            ) : recent.length ? (
              <div className="p4-list">
                {recent.map(item => (
                  <Link key={item.id} to={`/result/${item.id}`} className="p4-list-row" style={{ borderRadius: '10px' }}>
                    <span className="p4-list-icon">
                      <Activity size={18} />
                    </span>
                    <span>
                      <strong>
                        {item.crop} · {item.field}
                      </strong>
                      <small>
                        {item.crop_health?.finding.possible_problem ?? `Analysis ${item.status}`} ·{' '}
                        {new Date(item.created_at).toLocaleDateString('en-IN')}
                      </small>
                    </span>
                    <span
                      className={`source-badge source-${
                        item.is_synthetic ? 'demo' : item.crop_health?.source === 'AI LIVE' ? 'live' : 'fallback'
                      }`}
                    >
                      {item.is_synthetic ? t('synthetic') : item.crop_health?.source ?? item.status}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState
                title={t('noReportsYet')}
                body={t('yourObservationsHere')}
                action={
                  <Link className="button secondary" to="/report">
                    {t('createReport')}
                  </Link>
                }
              />
            )}
          </Panel>
        </Card3D>

        <Card3D intensity={8}>
          <Panel style={{ height: '100%' }}>
            <SectionHead title={t('nearbyCottonActivity')} to="/alerts" />
            {alerts.isPending && coordinates ? (
              <Skeleton className="p4-signal-skeleton" />
            ) : alerts.data?.length ? (
              <div className="p4-list">
                {alerts.data.slice(0, 3).map(item => (
                  <Link className="p4-list-row" to="/alerts" key={item.id} style={{ borderRadius: '10px' }}>
                    <span className="p4-list-icon">
                      <MapPin size={18} />
                    </span>
                    <span>
                      <strong>{item.possible_problem}</strong>
                      <small>
                        {item.cluster_size} {t('reports').toLowerCase()} · {item.distance_km.toFixed(1)} km · {item.district}
                      </small>
                    </span>
                    <span className={`source-badge source-${item.is_synthetic ? 'demo' : 'live'}`}>
                      {item.is_synthetic ? t('synthetic') : 'REPORTED'}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="p4-muted">{alerts.isError ? t('nearbyUnavailable') : t('noMatchingClusters')}</p>
            )}
          </Panel>
        </Card3D>
      </div>
    </motion.div>
  )
}
