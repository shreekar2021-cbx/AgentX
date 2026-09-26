import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Bell, Check } from 'lucide-react'
import { api } from '../../lib/api'
import { useTranslation } from '../../lib/i18n'
import { EmptyState, PageHeader, Panel, Skeleton } from '../../components/UI'

export default function Notifications() {
  const { t } = useTranslation()
  const client = useQueryClient()
  const query = useQuery({ queryKey: ['notifications'], queryFn: api.notifications, refetchInterval: 30_000 })
  async function markRead(id: string) { await api.markNotificationRead(id); await client.invalidateQueries({ queryKey: ['notifications'] }) }
  return <div className="page"><PageHeader eyebrow="YOUR FARM / UPDATES" title={t('notificationsTitle')} description={t('notificationsDescription')}/>{query.isPending ? <Skeleton className="result-loading"/> : query.isError ? <EmptyState title={t('notificationsPageUnavailable')} body={query.error.message} action={<button className="button secondary" onClick={() => query.refetch()}>{t('retry')}</button>}/> : query.data.length ? <Panel className="narrow-panel">{query.data.map(item => <div className={`p3-notification ${item.read_at ? 'is-read' : ''}`} key={item.id}><span className="signal-icon amber"><Bell size={18}/></span><div><strong>{item.title}</strong>{item.is_synthetic && <span className="source-badge source-demo">SYNTHETIC DEMO</span>}<p>{item.body}</p><small>{new Date(item.created_at).toLocaleString('en-IN')} · {item.kind.replace('_', ' ')}</small>{item.target_url && <Link to={item.target_url}>{t('openReport')}</Link>}</div>{!item.read_at && <button className="button secondary" aria-label={`Mark ${item.title} read`} onClick={() => markRead(item.id)}><Check size={16}/></button>}</div>)}</Panel> : <EmptyState title={t('noNotificationsTitle')} body={t('noNotificationsBody')}/>}</div>
}
