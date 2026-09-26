import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Activity, ArrowLeft, CalendarDays, CloudSun, Compass, Info, MapPin, ShieldCheck, Volume2, VolumeX } from 'lucide-react'
import { api } from '../../lib/api'
import type { LiveReport } from '../../lib/types'
import { EmptyState, Eyebrow, PageHeader, Panel, SectionHead, SeverityBadge, Skeleton, SourceBadge } from '../../components/UI'
import { useTranslation } from '../../lib/i18n'
import { speakText, stopSpeaking, speechAvailable } from '../../lib/voice'

function SourcePill({ source }: { source: string }) { return <span className={`source-badge ${source === 'AI LIVE' ? 'source-live' : source === 'AI CACHED' ? 'source-cached' : 'source-fallback'}`}>{source}</span> }
const titleCase = (value: string) => value.charAt(0).toUpperCase() + value.slice(1) as 'Low' | 'Moderate' | 'High'

function ResultContent({ report }: { report: LiveReport }) {
  const { t, language } = useTranslation()
  const [tab, setTab] = useState<'Overview' | 'Monitoring'>('Overview')
  const [speaking, setSpeaking] = useState(false)
  const analysis = report.crop_health
  if (!analysis) return <EmptyState title={t('analysisNotComplete')} body={`Current stage: ${report.stage}. Open this report again after analysis finishes.`} action={<Link className="button secondary" to="/reports">{t('reports')}</Link>}/>
  const finding = analysis.finding
  const weather = report.weather
  const risk = report.risk
  const outbreak = report.outbreak

  function toggleSpeech() {
    if (speaking) {
      stopSpeaking()
      setSpeaking(false)
      return
    }
    const script = `${finding.possible_problem}. ${finding.immediate_actions.join('. ')}`
    setSpeaking(true)
    speakText(script, language as 'en' | 'te' | 'hi', {
      onEnd: () => setSpeaking(false),
      onError: () => setSpeaking(false),
    })
  }

  return <><div className="result-source-line"><SourcePill source={analysis.source}/>{report.is_synthetic && <span className="source-badge source-demo">{t('syntheticSampleReport')}</span>}<span>{analysis.image_assessed ? t('imageAssessed') : t('textOnlyAssessed')}</span></div>{analysis.limitation && <div className="demo-notice"><Info size={16}/><span>{analysis.limitation}</span></div>}{report.nearby_synthetic_count > 0 && <div className="demo-notice"><Info size={16}/><span>{report.nearby_synthetic_count} nearby matches come from the synthetic development network. They are not real farmer observations.</span><SourceBadge/></div>}
    <div className="result-grid"><div className="result-main"><Panel className="result-hero"><div className="result-image"><img src={report.image_url ?? '/images/crop.svg'} alt={report.image_url ? "Uploaded crop observation" : "Crop illustration placeholder"} onError={event => { event.currentTarget.src = '/images/crop.svg' }}/><span>{report.is_synthetic ? report.image_url ? t('syntheticDemoImage') : t('syntheticDemoImage') : report.image_url ? t('fieldImagePrivate') : t('imageUnavailable')}</span></div><div className="result-summary"><Eyebrow>{t('possibleIssue')} / {analysis.source}</Eyebrow><h2>{finding.possible_problem}</h2><div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '8px 0' }}><button className="button secondary" onClick={toggleSpeech} disabled={!speechAvailable()} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '13px', padding: '6px 12px' }}>{speaking ? <VolumeX size={15}/> : <Volume2 size={15}/>}{speaking ? t('stopSpeaking') : t('listenToDiagnosis')}</button></div><p>{t('resultSubtext')}</p><div className="result-tags"><SeverityBadge severity={titleCase(finding.severity)}/><span className="confidence">{analysis.source.startsWith('AI') ? t('aiConfidence') : t('textMatchStrength')} <strong>{Math.round(finding.confidence * 100)}%</strong></span></div><div className="result-identity"><div><small>{t('cropLabel')}</small><strong>{report.crop}</strong></div><div><small>{t('fieldLabel')}</small><strong>{report.field}</strong></div><div><small>{t('reportLabel')}</small><strong>{report.id.slice(0, 8)}</strong></div></div></div></Panel><div className="tab-row"><button className={tab === 'Overview' ? 'selected' : ''} onClick={() => setTab('Overview')}>{t('overviewTab')}</button><button className={tab === 'Monitoring' ? 'selected' : ''} onClick={() => setTab('Monitoring')}>{t('monitoringPlanTab')}</button></div>{tab === 'Overview' ? <><div className="two-col"><Panel className="detail-panel"><div className="detail-icon amber"><Activity size={20}/></div><h3>{t('observedSymptomPattern')}</h3><ul>{finding.symptoms.map(item => <li key={item}>{item}</li>)}</ul></Panel><Panel className="detail-panel"><div className="detail-icon blue"><Compass size={20}/></div><h3>{t('possibleCauses')}</h3><ul>{finding.possible_causes.map(item => <li key={item}>{item}</li>)}</ul></Panel></div><Panel className="action-panel"><SectionHead title={t('suggestedActions')}/><div className="numbered-actions">{finding.immediate_actions.map((item, index) => <div key={index}><span>{String(index + 1).padStart(2, '0')}</span><p>{item}</p></div>)}</div></Panel><Panel className="detail-panel"><h3>{t('precautions')}</h3><ul>{finding.precautions.map(item => <li key={item}>{item}</li>)}</ul></Panel></> : <Panel className="action-panel"><SectionHead title={t('monitoringPlan')}/><div className="timeline">{finding.monitoring.map((item, index) => <div key={index}><span>CHECK {String(index + 1).padStart(2, '0')}</span><strong>{item}</strong></div>)}</div></Panel>}</div><aside className="result-aside"><Panel className="context-card"><SectionHead title={t('fieldContext')}/><div className="context-row"><CloudSun size={18}/><span>{t('weather')}</span><strong>{weather?.current ? `${Math.round(weather.current.temperature_c)}°C · ${weather.current.relative_humidity_pct}% RH` : t('unavailable')}</strong></div><div className="context-row"><MapPin size={18}/><span>{t('nearbyMatches')}</span><strong>{report.nearby_count} {t('within10km')}</strong></div><div className="context-row"><CalendarDays size={18}/><span>{t('reported')}</span><strong>{new Date(report.created_at).toLocaleDateString('en-IN')}</strong></div><div className="context-row"><ShieldCheck size={18}/><span>{t('weatherSource')}</span><strong>{weather?.source ?? t('unavailable')}{weather?.stale ? ' · stale' : ''}</strong></div></Panel><Panel className="context-card"><SectionHead title={t('riskIndicators')}/><div className="context-row"><span>{t('individualRisk')}</span><strong>{risk?.individual_risk ?? '—'} / 100</strong></div><div className="context-row"><span>{t('communityRisk')}</span><strong>{risk?.community_risk ?? '—'} / 100</strong></div><div className="context-row"><span>{t('spreadPotential')}</span><strong>{finding.spread_potential}</strong></div>{risk?.risk_factors.map(item => <p className="risk-factor" key={item}>• {item}</p>)}</Panel><Panel className="expert-card"><div className="expert-icon"><ShieldCheck size={24}/></div><h3>{t('expertVerification')}</h3><p>{finding.expert_verification}</p><span>{t('advisoryNotDiagnosis')}</span></Panel><Panel className="your-note"><h3>{t('nearbyClusterCheck')}</h3><p>{outbreak?.alert_reason ?? t('noClusterResult')}</p>{outbreak?.evidence_is_synthetic && <span className="source-badge source-demo">SYNTHETIC EVIDENCE</span>}</Panel><Panel className="your-note"><h3>{t('yourFieldNote')}</h3><p>{report.symptom_description}</p></Panel></aside></div>
  </>
}

export default function CropResult() {
  const { t } = useTranslation()
  const { id } = useParams()
  const query = useQuery({ queryKey: ['report', id], queryFn: () => api.report(id!), enabled: Boolean(id), refetchInterval: data => data.state.data?.status === 'processing' ? 1000 : false })
  return <div className="page"><Link className="back-link" to="/reports"><ArrowLeft size={16}/> {t('backToReports')}</Link><PageHeader eyebrow={t('cropHealthFieldResult')} title={t('cropObservation')} description={t('cropResultDescription')} action={query.data?.crop_health && <SourcePill source={query.data.crop_health.source}/>}/>{query.isPending ? <><Skeleton className="result-loading"/><Skeleton className="result-loading short"/></> : query.isError ? <EmptyState title={t('reportUnavailable')} body={query.error.message} action={<Link className="button secondary" to="/reports">{t('reports')}</Link>}/> : <ResultContent report={query.data}/>}</div>
}
