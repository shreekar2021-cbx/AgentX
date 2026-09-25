import { Link } from 'react-router-dom'
import { CloudOff, Languages, RefreshCw, ShieldCheck } from 'lucide-react'
import { useUI } from '../../lib/store'
import { useTranslation } from '../../lib/i18n'
import { useQueueStatus } from '../../lib/useQueueStatus'
import { PageHeader, Panel, SectionHead } from '../../components/UI'

export default function SettingsPage() {
  const { language, setLanguage } = useUI()
  const { t } = useTranslation()
  const queue = useQueueStatus()
  return <div className="page"><PageHeader eyebrow="WORKSPACE / PREFERENCES" title={t('settings')} description="Language, connectivity, and data source preferences for this device."/><div className="p3-profile-grid"><Panel><SectionHead title="Language"/><div className="p3-settings-symbol"><Languages size={22}/></div><label className="field-label">Choose interface language<select value={language} onChange={event => setLanguage(event.target.value as 'en' | 'te' | 'hi')}><option value="en">English</option><option value="te">తెలుగు</option><option value="hi">हिन्दी</option></select></label><p>Navigation and essential report actions use local translations. Agricultural result text remains in its source language and should be reviewed with a local expert.</p></Panel><Panel><SectionHead title="Connectivity and offline reports"/><div className="p3-settings-symbol"><CloudOff size={22}/></div><div className="admin-line"><span>Connection</span><strong>{queue.online ? t('online') : t('offline')}</strong></div><div className="admin-line"><span>Reports on this device</span><strong>{queue.count} {t('waitingSync')}</strong></div><p>Queued reports and images stay in this browser's IndexedDB until analysis completes. The app shell and curated crop reference are available after installation and a successful online visit.</p><Link to="/reports" className="button secondary"><RefreshCw size={16}/>{t('syncNow')}</Link></Panel></div><Panel><SectionHead title="Data and provider status"/><div className="p3-settings-symbol"><ShieldCheck size={22}/></div><p>Source labels distinguish live observations, caches, dated synthetic examples, and curated static knowledge. Check the timestamp before field or market decisions.</p><Link to="/admin" className="button secondary">View provider health</Link></Panel></div>
}
