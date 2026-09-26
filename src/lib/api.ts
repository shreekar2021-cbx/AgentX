import type { AdminOverview, AnalysisEvent, ApiError, FarmProfile, FarmProfileInput, FertilizerRecommendation, HealthResponse, LiveReport, MarketEstimate, MarketEstimateInput, MarketResponse, MarketTrend, NearbyCluster, NotificationItem, PortfolioCrop, PortfolioInput, ProviderHealth, SeedRecommendation, TranslationRequest, TranslationResponse, VoiceAssistRequest, VoiceAssistResponse, VoiceStatusResponse, WeatherResult } from './types'
const baseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
let accessToken: string | null = null
export function setApiAccessToken(token: string | null) { accessToken = token }
export class ApiRequestError extends Error { constructor(public status: number, public detail: ApiError) { super(detail.message) } }
function headers(extra?: HeadersInit): HeadersInit { return { ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}), ...extra } }
async function errorFor(response: Response): Promise<ApiRequestError> {
  const body = await response.json().catch(() => ({})) as { code?: string; message?: string; detail?: unknown; request_id?: string }
  return new ApiRequestError(response.status, { code: body.code ?? 'http_error', message: body.message ?? (typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`), request_id: body.request_id })
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(`${baseUrl}/api${path}`, { ...init, headers: headers(init?.headers) }) }
  catch { throw new ApiRequestError(0, { code: 'network_error', message: 'Cannot reach the AgriVision API.' }) }
  if (!response.ok) throw await errorFor(response)
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
export const api = {
  health: () => request<HealthResponse>('/health'),
  capabilities: () => request<{ capabilities: Record<string, string> }>('/capabilities'),
  async knowledgeCrops(): Promise<{ source: string; version: string; crops: { name: string; stages: string[]; seasons: string[] }[]; issue_count: number }> {
    try { return await request('/knowledge/crops') }
    catch (error) {
      try {
        const response = await fetch('/knowledge/essential-crops.json')
        if (!response.ok) throw error
        const data = await response.json() as { version: string; crops: { name: string; stages: string[]; seasons: string[]; issues: unknown[] }[] }
        return { source: 'CURATED STATIC OFFLINE', version: data.version, crops: data.crops.map(item => ({ name: item.name, stages: item.stages, seasons: item.seasons })), issue_count: data.crops.reduce((count, item) => count + item.issues.length, 0) }
      } catch { throw error }
    }
  },
  createReport: (form: FormData) => request<LiveReport>('/reports', { method: 'POST', body: form }),
  reports: () => request<LiveReport[]>('/reports'),
  report: (id: string) => request<LiveReport>(`/reports/${encodeURIComponent(id)}`),
  analyze: (id: string) => request<LiveReport>(`/reports/${encodeURIComponent(id)}/analyze`, { method: 'POST' }),
  weather: (latitude: number, longitude: number) => request<WeatherResult>(`/weather?latitude=${latitude}&longitude=${longitude}`),
  nearbyAlerts: (crop: string, latitude: number, longitude: number, radius = 10) => request<NearbyCluster[]>(`/alerts/nearby?crop=${encodeURIComponent(crop)}&latitude=${latitude}&longitude=${longitude}&radius_km=${radius}`),
  farmProfile: () => request<FarmProfile | null>('/farms/profile'),
  saveFarmProfile: (profile: FarmProfileInput) => request<FarmProfile>('/farms/profile', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) }),
  portfolio: () => request<PortfolioCrop[]>('/portfolio'),
  addCrop: (crop: PortfolioInput) => request<PortfolioCrop>('/portfolio', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(crop) }),
  updateCrop: (id: string, crop: PortfolioInput) => request<PortfolioCrop>(`/portfolio/${encodeURIComponent(id)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(crop) }),
  deleteCrop: (id: string) => request<void>(`/portfolio/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  marketPrices: (commodity: string, district?: string, latitude?: number, longitude?: number) => request<MarketResponse>(`/market/prices?${new URLSearchParams({ commodity, ...(district && district !== 'All' ? { district } : {}), ...(latitude !== undefined && longitude !== undefined ? { latitude: String(latitude), longitude: String(longitude) } : {}) })}`),
  marketTrend: (commodity: string, district?: string) => request<MarketTrend>('/market/trend', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ commodity, district: district === 'All' ? null : district }) }),
  marketEstimate: (values: MarketEstimateInput) => request<MarketEstimate>('/market/estimate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) }),
  seedRecommendation: (profile: FarmProfileInput) => request<SeedRecommendation>('/recommendations/seed', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) }),
  fertilizerRecommendation: (profile: FarmProfileInput) => request<FertilizerRecommendation>('/recommendations/fertilizer', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(profile) }),
  notifications: () => request<NotificationItem[]>('/notifications'),
  markNotificationRead: (id: string) => request<NotificationItem>(`/notifications/${encodeURIComponent(id)}/read`, { method: 'PATCH' }),
  providerHealth: () => request<ProviderHealth>('/provider-health'),
  adminOverview: () => request<AdminOverview>('/admin/overview'),
  voiceStatus: () => request<VoiceStatusResponse>('/voice/status'),
  voiceAssist: (payload: VoiceAssistRequest) => request<VoiceAssistResponse>('/voice/assist', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
  translate: (payload: TranslationRequest) => request<TranslationResponse>('/voice/translate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }),
  async streamAnalysis(id: string, onEvent: (event: AnalysisEvent) => void): Promise<LiveReport> {
    let response: Response
    try { response = await fetch(`${baseUrl}/api/reports/${encodeURIComponent(id)}/analyze/stream`, { method: 'POST', headers: headers() }) }
    catch { throw new ApiRequestError(0, { code: 'network_error', message: 'Cannot reach the analysis service.' }) }
    if (!response.ok) throw await errorFor(response)
    if (!response.body) throw new ApiRequestError(0, { code: 'stream_unavailable', message: 'Analysis stream is unavailable.' })
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let pending = ''; let result: LiveReport | null = null
    while (true) {
      const { value, done } = await reader.read(); pending += decoder.decode(value, { stream: !done })
      const lines = pending.split('\n'); pending = lines.pop() ?? ''
      for (const line of lines) { if (!line.trim()) continue; const event = JSON.parse(line) as AnalysisEvent; onEvent(event); if (event.stage === 'error') throw new ApiRequestError(500, { code: 'analysis_failed', message: event.message ?? 'Analysis failed.' }); if (event.report) result = event.report }
      if (done) break
    }
    if (!result) throw new ApiRequestError(500, { code: 'analysis_incomplete', message: 'Analysis ended without a result.' })
    return result
  },
}
