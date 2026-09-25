import { api, ApiRequestError } from './api'

const DATABASE = 'agrivision-offline-v1'
const STORE = 'reports'
export const QUEUE_EVENT = 'agrivision:queue-change'

export interface QueuedReport {
  id: string
  crop: string
  field: string
  district: string
  symptoms: string
  notes: string
  latitude: string
  longitude: string
  image: Blob
  imageName: string
  imageType: string
  demoSample?: boolean
  createdAt: string
  status: 'waiting' | 'syncing' | 'failed'
  serverId?: string
  lastError?: string
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in globalThis)) { reject(new Error('Offline storage is unavailable in this browser.')); return }
    const request = indexedDB.open(DATABASE, 1)
    request.onupgradeneeded = () => { if (!request.result.objectStoreNames.contains(STORE)) request.result.createObjectStore(STORE, { keyPath: 'id' }) }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('Could not open offline storage.'))
  })
}

async function transact<T>(mode: IDBTransactionMode, operation: (store: IDBObjectStore, done: (value: T) => void) => void): Promise<T> {
  const database = await openDatabase()
  return new Promise<T>((resolve, reject) => {
    const transaction = database.transaction(STORE, mode)
    let value: T
    operation(transaction.objectStore(STORE), result => { value = result })
    transaction.oncomplete = () => { database.close(); resolve(value) }
    transaction.onerror = () => { database.close(); reject(transaction.error ?? new Error('Offline storage failed.')) }
    transaction.onabort = () => { database.close(); reject(transaction.error ?? new Error('Offline storage was interrupted.')) }
  })
}

function changed() { if (typeof window !== 'undefined') window.dispatchEvent(new Event(QUEUE_EVENT)) }

export async function listQueuedReports(): Promise<QueuedReport[]> {
  const rows = await transact<QueuedReport[]>('readonly', (store, done) => {
    const request = store.getAll()
    request.onsuccess = () => done(request.result as QueuedReport[])
  })
  return rows.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
}

async function save(item: QueuedReport): Promise<void> {
  await transact<void>('readwrite', (store, done) => { store.put(item); done() })
  changed()
}

async function remove(id: string): Promise<void> {
  await transact<void>('readwrite', (store, done) => { store.delete(id); done() })
  changed()
}

export async function queueReport(item: Omit<QueuedReport, 'createdAt' | 'status'>): Promise<QueuedReport> {
  const queued: QueuedReport = { ...item, createdAt: new Date().toISOString(), status: 'waiting' }
  await save(queued)
  return queued
}

let activeSync: Promise<{ synced: number; failed: number }> | null = null

export function syncQueuedReports(): Promise<{ synced: number; failed: number }> {
  if (activeSync) return activeSync
  activeSync = runSync().finally(() => { activeSync = null })
  return activeSync
}

async function runSync(): Promise<{ synced: number; failed: number }> {
  if (typeof navigator !== 'undefined' && !navigator.onLine) return { synced: 0, failed: 0 }
  let synced = 0, failed = 0
  for (const original of await listQueuedReports()) {
    const item = { ...original, status: 'syncing' as const, lastError: undefined }
    await save(item)
    try {
      if (!item.serverId) {
        const form = new FormData()
        for (const key of ['crop', 'field', 'district', 'symptoms', 'notes', 'latitude', 'longitude'] as const) form.set(key, item[key])
        form.set('client_mutation_id', item.id)
        form.set('demo_sample', String(Boolean(item.demoSample)))
        form.set('image', new File([item.image], item.imageName, { type: item.imageType }))
        const created = await api.createReport(form)
        item.serverId = created.id
        await save(item)
      }
      const result = await api.analyze(item.serverId)
      if (result.status !== 'completed') throw new Error(`Analysis remains ${result.status}.`)
      await remove(item.id)
      synced++
    } catch (error) {
      failed++
      await save({ ...item, status: 'failed', lastError: error instanceof Error ? error.message : 'Sync failed.' })
      if (error instanceof ApiRequestError && error.status === 0) break
    }
  }
  return { synced, failed }
}
