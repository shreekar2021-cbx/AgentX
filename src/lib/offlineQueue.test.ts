import 'fake-indexeddb/auto'
import { describe, expect, it, vi } from 'vitest'

const { createReport, analyze } = vi.hoisted(() => ({ createReport: vi.fn(), analyze: vi.fn() }))
vi.mock('./api', () => ({ api: { createReport, analyze }, ApiRequestError: class ApiRequestError extends Error { constructor(public status: number, message: string) { super(message) } } }))

import { listQueuedReports, queueReport, syncQueuedReports } from './offlineQueue'

describe('offline report queue', () => {
  it('keeps a report offline, then resumes after analysis fails without posting twice', async () => {
    vi.stubGlobal('navigator', { onLine: false })
    const id = crypto.randomUUID()
    await queueReport({ id, crop: 'Cotton', field: 'North Field', district: 'Rangareddy', symptoms: 'White insects beneath leaves', notes: '', latitude: '17.25', longitude: '78.39', image: new Blob(['image'], { type: 'image/png' }), imageName: 'crop.png', imageType: 'image/png' })
    expect((await listQueuedReports())[0].status).toBe('waiting')
    expect(await syncQueuedReports()).toEqual({ synced: 0, failed: 0 })
    expect(createReport).not.toHaveBeenCalled()
    vi.stubGlobal('navigator', { onLine: true })
    createReport.mockResolvedValue({ id: 'server-report' })
    analyze.mockRejectedValueOnce(new Error('temporary analysis failure')).mockResolvedValueOnce({ status: 'completed' })
    const first = await syncQueuedReports()
    expect(first.failed).toBe(1)
    expect((await listQueuedReports())[0]).toMatchObject({ id, serverId: 'server-report', status: 'failed' })
    const second = await syncQueuedReports()
    expect(second.synced).toBe(1)
    expect(await listQueuedReports()).toEqual([])
    expect(createReport).toHaveBeenCalledTimes(1)
    const form = createReport.mock.calls[0][0] as FormData
    expect(form.get('client_mutation_id')).toBe(id)
    vi.unstubAllGlobals()
  })
})
