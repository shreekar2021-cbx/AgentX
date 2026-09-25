import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { listQueuedReports, QUEUE_EVENT, syncQueuedReports } from './offlineQueue'

export function useQueueStatus() {
  const [online, setOnline] = useState(() => navigator.onLine)
  const [count, setCount] = useState(0)
  const queryClient = useQueryClient()
  useEffect(() => {
    let active = true
    const refresh = () => { listQueuedReports().then(items => { if (active) setCount(items.length) }).catch(() => { if (active) setCount(0) }) }
    const reconnect = () => { setOnline(true); void syncQueuedReports().then(() => { refresh(); void queryClient.invalidateQueries({ queryKey: ['reports'] }); void queryClient.invalidateQueries({ queryKey: ['notifications'] }) }).catch(() => refresh()) }
    const disconnect = () => setOnline(false)
    refresh()
    if (navigator.onLine) reconnect()
    window.addEventListener(QUEUE_EVENT, refresh)
    window.addEventListener('online', reconnect)
    window.addEventListener('offline', disconnect)
    return () => { active = false; window.removeEventListener(QUEUE_EVENT, refresh); window.removeEventListener('online', reconnect); window.removeEventListener('offline', disconnect) }
  }, [queryClient])
  return { online, count, sync: syncQueuedReports }
}
