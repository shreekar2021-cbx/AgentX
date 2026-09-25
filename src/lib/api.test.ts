import { afterEach, expect, it, vi } from 'vitest'
import { api } from './api'

afterEach(() => vi.unstubAllGlobals())

it('uses the precached curated crop catalog when the API is offline', async () => {
  const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError('offline')).mockResolvedValueOnce({ ok: true, json: async () => ({ version: '2026-09-26', crops: [{ name: 'Cotton', stages: ['flowering'], seasons: ['kharif'], issues: [{ name: 'Whitefly' }] }] }) })
  vi.stubGlobal('fetch', fetchMock)
  const result = await api.knowledgeCrops()
  expect(result.source).toBe('CURATED STATIC OFFLINE')
  expect(result.issue_count).toBe(1)
  expect(fetchMock).toHaveBeenCalledTimes(2)
  expect(fetchMock.mock.calls[1][0]).toBe('/knowledge/essential-crops.json')
})
