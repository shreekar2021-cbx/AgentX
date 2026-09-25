import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowDownRight, ArrowUpRight, Info, LocateFixed, MapPin, ShoppingBasket, TrendingUp } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Button, Card, PageHeading, Pill, SectionTitle, StatCard } from '../components/ui'
import { useAppStore } from '../store/useAppStore'
import { distanceKm, fetchMarketCommodities, fetchMarketHistory, fetchMarketPrices } from '../api/market'

const money = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })
const rupees = (value) => `₹${money.format(Number(value))}`

const statusTone = { LIVE: 'green', CACHED: 'amber', FALLBACK: 'gray' }

function sourceLabel(status) {
  return status || 'UNAVAILABLE'
}

function displayDate(date) {
  return date ? new Date(`${date}T00:00:00`).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '—'
}

function chartPoints(prices) {
  const perDay = new Map()
  for (const row of prices || []) {
    const dateValues = perDay.get(row.price_date) || []
    dateValues.push(Number(row.modal_price))
    perDay.set(row.price_date, dateValues)
  }
  return [...perDay.entries()]
    .sort(([dateA], [dateB]) => dateA.localeCompare(dateB))
    .map(([date, values]) => ({
      date: displayDate(date),
      price: values.reduce((total, value) => total + value, 0) / values.length,
    }))
}

export default function MarketIntelligence() {
  const preferredCrop = useAppStore((state) => state.selectedCrop)
  const [commodityId, setCommodityId] = useState('')
  const [selectedMandiId, setSelectedMandiId] = useState('')
  const [historyDays, setHistoryDays] = useState(7)
  const [draftState, setDraftState] = useState('')
  const [draftDistrict, setDraftDistrict] = useState('')
  const [filters, setFilters] = useState({ state: '', district: '' })
  const [location, setLocation] = useState(null)
  const [manualLatitude, setManualLatitude] = useState('')
  const [manualLongitude, setManualLongitude] = useState('')
  const [locationMessage, setLocationMessage] = useState('')

  const commoditiesQuery = useQuery({
    queryKey: ['market', 'commodities'],
    queryFn: ({ signal }) => fetchMarketCommodities(signal),
    staleTime: 5 * 60_000,
  })
  const commodities = commoditiesQuery.data || []

  useEffect(() => {
    if (!commodities.length) return
    if (commodities.some((commodity) => commodity.id === commodityId)) return
    const preferred = commodities.find((commodity) => (
      commodity.code.toLowerCase() === preferredCrop.toLowerCase()
      || commodity.name_en.toLowerCase() === preferredCrop.toLowerCase()
    ))
    setCommodityId((preferred || commodities[0]).id)
  }, [commodities, commodityId, preferredCrop])

  const pricesQuery = useQuery({
    queryKey: ['market', 'prices', commodityId, filters.state, filters.district],
    queryFn: ({ signal }) => fetchMarketPrices({
      commodityId,
      state: filters.state,
      district: filters.district || undefined,
    }, signal),
    enabled: Boolean(commodityId && filters.state),
  })
  const marketData = pricesQuery.data
  const prices = marketData?.prices || []

  useEffect(() => {
    if (!prices.length) {
      setSelectedMandiId('')
      return
    }
    if (prices.some((price) => price.mandi_id === selectedMandiId)) return
    setSelectedMandiId(prices.find((price) => price.mandi_id)?.mandi_id || '')
  }, [prices, selectedMandiId])

  const historyQuery = useQuery({
    queryKey: ['market', 'history', commodityId, selectedMandiId, historyDays],
    queryFn: ({ signal }) => fetchMarketHistory({
      commodityId,
      mandiId: selectedMandiId,
      days: historyDays,
    }, signal),
    enabled: Boolean(commodityId && selectedMandiId),
  })
  const allHistory = historyQuery.data?.prices || []
  const history = useMemo(() => chartPoints(allHistory), [allHistory])
  const newestPrice = [...prices].sort((a, b) => b.price_date.localeCompare(a.price_date))[0]
  const highestPrice = prices.reduce((best, price) => (
    !best || Number(price.modal_price) > Number(best.modal_price) ? price : best
  ), null)
  const averageModal = prices.length
    ? prices.reduce((sum, price) => sum + Number(price.modal_price), 0) / prices.length
    : null
  const historyChange = history.length > 1
    ? ((history.at(-1).price - history[0].price) / history[0].price) * 100
    : null
  const sortedPrices = useMemo(() => prices.map((price) => ({
    ...price,
    distance: location && price.mandi_latitude != null && price.mandi_longitude != null
      ? distanceKm(location.latitude, location.longitude, price.mandi_latitude, price.mandi_longitude)
      : null,
  })).sort((a, b) => {
    if (a.distance != null && b.distance != null) return a.distance - b.distance
    if (a.distance != null) return -1
    if (b.distance != null) return 1
    return b.price_date.localeCompare(a.price_date)
  }), [prices, location])
  const closestDistance = sortedPrices.find((price) => price.distance != null)?.distance
  const selectedCommodity = commodities.find((commodity) => commodity.id === commodityId)
  const selectedMandi = prices.find((price) => price.mandi_id === selectedMandiId)

  const applyFilters = (event) => {
    event.preventDefault()
    setFilters({ state: draftState.trim(), district: draftDistrict.trim() })
  }

  const useDeviceLocation = () => {
    if (!navigator.geolocation) {
      setLocationMessage('This browser does not provide location. Enter coordinates instead.')
      return
    }
    setLocationMessage('Waiting for location permission…')
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setLocation({ latitude: coords.latitude, longitude: coords.longitude })
        setManualLatitude(coords.latitude.toFixed(5))
        setManualLongitude(coords.longitude.toFixed(5))
        setLocationMessage('Using your device location for display distances.')
      },
      () => setLocationMessage('Location is unavailable. Enter coordinates manually to calculate distances.'),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 5 * 60_000 },
    )
  }

  const applyManualLocation = (event) => {
    event.preventDefault()
    const latitude = Number(manualLatitude)
    const longitude = Number(manualLongitude)
    if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90
      || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
      setLocationMessage('Enter a valid latitude (−90 to 90) and longitude (−180 to 180).')
      return
    }
    setLocation({ latitude, longitude })
    setLocationMessage('Using your manual coordinates for display distances.')
  }

  return <>
    <PageHeading
      eyebrow="Local mandi watch"
      title="Know your market"
      description="Compare current mandi prices and stored 7-day or 30-day price history."
    />

    <div className="mb-5 grid gap-4 xl:grid-cols-[1fr_1fr]">
      <Card>
        <SectionTitle>Market filters</SectionTitle>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="text-[11px] font-semibold text-muted">Crop / commodity
            <select value={commodityId} onChange={(event) => { setCommodityId(event.target.value); setSelectedMandiId('') }} className="mt-1.5 w-full rounded-xl border border-[#dfe8d9] bg-white px-3 py-2.5 text-sm text-ink" disabled={!commodities.length}>
              {commodities.length ? commodities.map((commodity) => <option key={commodity.id} value={commodity.id}>{commodity.name_en}</option>) : <option value="">No commodities available</option>}
            </select>
          </label>
          <label className="text-[11px] font-semibold text-muted">State
            <input value={draftState} onChange={(event) => setDraftState(event.target.value)} placeholder="e.g. Telangana" className="mt-1.5 w-full rounded-xl border border-[#dfe8d9] bg-white px-3 py-2.5 text-sm text-ink" />
          </label>
          <label className="text-[11px] font-semibold text-muted">District (optional)
            <input value={draftDistrict} onChange={(event) => setDraftDistrict(event.target.value)} placeholder="e.g. Warangal" className="mt-1.5 w-full rounded-xl border border-[#dfe8d9] bg-white px-3 py-2.5 text-sm text-ink" />
          </label>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Button onClick={applyFilters} disabled={!commodityId || !draftState.trim()}>Load mandi prices</Button>
          <p className="text-[10px] leading-4 text-muted">Prices are filtered by the selected state and optional district.</p>
        </div>
      </Card>

      <Card>
        <SectionTitle>Distance from your location</SectionTitle>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" onClick={useDeviceLocation}><LocateFixed size={15} />Use device location</Button>
          <span className="text-[10px] text-muted">or enter coordinates manually</span>
        </div>
        <form onSubmit={applyManualLocation} className="mt-3 grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
          <input aria-label="Latitude" inputMode="decimal" value={manualLatitude} onChange={(event) => setManualLatitude(event.target.value)} placeholder="Latitude" className="rounded-xl border border-[#dfe8d9] px-3 py-2 text-xs" />
          <input aria-label="Longitude" inputMode="decimal" value={manualLongitude} onChange={(event) => setManualLongitude(event.target.value)} placeholder="Longitude" className="rounded-xl border border-[#dfe8d9] px-3 py-2 text-xs" />
          <Button type="submit" variant="soft">Apply</Button>
        </form>
        <p className="mt-2 min-h-4 text-[10px] text-muted">{locationMessage || 'Distances are calculated in your browser when mandi coordinates are available.'}</p>
      </Card>
    </div>

    {commoditiesQuery.isError && <div role="alert" className="mb-4 flex items-center justify-between rounded-xl border border-red-100 bg-red-50 p-3 text-xs text-red-700">
      <span>{commoditiesQuery.error.message}</span><Button variant="ghost" onClick={() => commoditiesQuery.refetch()}>Retry</Button>
    </div>}
    {pricesQuery.isError && <div role="alert" className="mb-4 flex items-center justify-between rounded-xl border border-amber-100 bg-amber-50 p-3 text-xs text-amber-800">
      <span>{pricesQuery.error.message}{marketData ? ' Showing the last loaded prices.' : ''}</span><Button variant="ghost" onClick={() => pricesQuery.refetch()}>Retry</Button>
    </div>}

    {marketData && prices.length > 0 && <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#e9eee5] bg-white px-4 py-3">
      <div className="flex items-center gap-2"><span className="text-[11px] font-semibold text-muted">Current price source</span><Pill tone={statusTone[marketData.source_status] || 'gray'}>{sourceLabel(marketData.source_status)}</Pill>{marketData.is_stale && <Pill tone="amber">Stale observations</Pill>}</div>
      <span className="text-[10px] text-muted">Latest observation: {displayDate(marketData.as_of)}</span>
    </div>}

    <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard label="Highest listed modal" value={highestPrice ? rupees(highestPrice.modal_price) : '—'} detail={highestPrice?.market_name || 'Load market prices'} icon={TrendingUp} />
      <StatCard label="Average modal price" value={averageModal == null ? '—' : rupees(averageModal)} detail={`${prices.length} mandi observations`} icon={ShoppingBasket} tone="amber" />
      <StatCard label="Closest mandi" value={closestDistance == null ? '—' : `${closestDistance.toFixed(1)} km`} detail={closestDistance == null ? 'Location and mandi coordinates needed' : 'Straight-line display distance'} icon={MapPin} tone="blue" />
      <StatCard label={`${historyDays}-day price direction`} value={historyChange == null ? '—' : `${historyChange > 0 ? '+' : ''}${historyChange.toFixed(1)}%`} detail={history.length > 1 ? 'First to latest stored observation' : 'Not enough history yet'} icon={historyChange != null && historyChange < 0 ? ArrowDownRight : ArrowUpRight} tone={historyChange != null && historyChange < 0 ? 'red' : 'green'} />
    </div>

    <div className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
      <Card>
        <SectionTitle action={<div className="flex rounded-lg bg-[#f4f6f1] p-1">
          {[7, 30].map((days) => <button key={days} onClick={() => setHistoryDays(days)} className={`rounded-md px-3 py-1.5 text-[10px] font-bold ${historyDays === days ? 'bg-white text-leaf-700 shadow-sm' : 'text-muted'}`}>{days} days</button>)}
        </div>}>Price history <Pill tone={historyQuery.data?.source_status === 'CACHED' ? 'amber' : 'gray'}>{historyQuery.data?.source_status || '—'}</Pill></SectionTitle>
        {selectedMandi && <p className="-mt-2 mb-3 text-xs text-muted">{selectedCommodity?.name_en} at {selectedMandi.market_name} · INR/quintal</p>}
        {historyQuery.isLoading && <div className="h-[230px] animate-pulse rounded-xl bg-[#f5f7f2]" />}
        {!historyQuery.isLoading && history.length > 0 && <>
          <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2"><p className="text-2xl font-extrabold text-ink">{rupees(history.at(-1).price)} <span className="text-xs font-semibold text-muted">/ quintal</span></p><span className="text-[10px] text-muted">{history.length} dated observations</span></div>
          <div className="h-[230px] w-full"><ResponsiveContainer width="100%" height="100%"><AreaChart data={history} margin={{ top: 12, right: 6, left: -16, bottom: 0 }}><defs><linearGradient id="marketPriceFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#79aa58" stopOpacity={0.22} /><stop offset="95%" stopColor="#79aa58" stopOpacity={0} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#edf1e9" strokeDasharray="4 5" /><XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#96a299' }} dy={9} /><YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#96a299' }} tickFormatter={(value) => `${Math.round(value / 1000)}k`} /><Tooltip formatter={(value) => [rupees(value), 'Average modal']} contentStyle={{ borderRadius: 12, border: '1px solid #e9eee5', fontSize: 12, boxShadow: '0 8px 30px rgba(36, 61, 45, .08)' }} /><Area type="monotone" dataKey="price" stroke="#5f9644" strokeWidth={2.5} fill="url(#marketPriceFill)" activeDot={{ r: 5, strokeWidth: 3 }} /></AreaChart></ResponsiveContainer></div>
        </>}
        {!historyQuery.isLoading && (!history.length || !selectedMandiId) && <div className="flex h-[230px] flex-col items-center justify-center rounded-xl bg-[#f7f9f5] px-6 text-center"><Info size={18} className="text-muted" /><p className="mt-2 text-sm font-bold text-ink">{selectedMandiId ? `No ${historyDays}-day price history yet` : 'Select a mandi with a stored ID'}</p><p className="mt-1 max-w-sm text-xs leading-5 text-muted">History comes from stored AGMARKNET observations. It will appear after observations have been collected for this crop and mandi.</p></div>}
        {historyQuery.isError && <p role="alert" className="mt-2 text-xs text-amber-700">{historyQuery.error.message}</p>}
        <p className="mt-3 flex items-center gap-1 text-[10px] text-muted"><Info size={12} />Historical prices are observations, not forecasts.</p>
      </Card>

      <Card>
        <SectionTitle>Market snapshot</SectionTitle>
        {!filters.state && <p className="rounded-xl bg-[#f7f9f5] p-4 text-xs leading-5 text-muted">Enter a state and load prices to see the latest mandi snapshot.</p>}
        {filters.state && pricesQuery.isLoading && <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-12 animate-pulse rounded-xl bg-[#f5f7f2]" />)}</div>}
        {filters.state && !pricesQuery.isLoading && !pricesQuery.isError && !prices.length && <p className="rounded-xl bg-[#f7f9f5] p-4 text-xs leading-5 text-muted">No prices are available for this crop and area yet.</p>}
        {prices.length > 0 && <>
          <div className="rounded-xl bg-[#f5f8f1] p-4"><div className="flex items-center gap-2"><span className="rounded-lg bg-white p-2 text-leaf-700"><TrendingUp size={15} /></span><p className="text-xs font-bold text-ink">{selectedCommodity?.name_en} · {filters.district || filters.state}</p></div><p className="mt-3 text-xs leading-5 text-[#647268]">{newestPrice ? `Most recent listed modal price: ${rupees(newestPrice.modal_price)} at ${newestPrice.market_name}.` : 'No current observations are available.'}</p><p className="mt-2 text-[10px] text-muted">Price date: {displayDate(newestPrice?.price_date)}</p></div>
          <div className="mt-5"><p className="mb-3 text-[10px] font-extrabold uppercase tracking-wider text-[#9aa69c]">Current mandi quotes</p><div className="space-y-3">{sortedPrices.slice(0, 4).map((price, index) => <button type="button" onClick={() => price.mandi_id && setSelectedMandiId(price.mandi_id)} key={`${price.provider_key}-${price.price_date}-${index}`} className={`flex w-full items-center justify-between gap-2 rounded-xl border p-3 text-left ${price.mandi_id === selectedMandiId ? 'border-leaf-300 bg-leaf-50/60' : 'border-[#eff2ec] bg-white'}`}><div className="flex min-w-0 items-center gap-2.5"><span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[10px] font-extrabold ${index === 0 ? 'bg-leaf-50 text-leaf-700' : 'bg-[#f5f7f2] text-muted'}`}>{index + 1}</span><div className="min-w-0"><p className="truncate text-[11px] font-bold text-ink">{price.market_name}</p><p className="mt-0.5 truncate text-[9px] text-muted">{price.district || price.state} · {price.distance == null ? 'Distance unavailable' : `${price.distance.toFixed(1)} km`}</p></div></div><div className="shrink-0 text-right"><p className="text-xs font-extrabold text-ink">{rupees(price.modal_price)}</p><p className="mt-0.5 text-[9px] text-muted">{displayDate(price.price_date)}</p></div></button>)}</div></div>
        </>}
      </Card>
    </div>

    <Card className="mt-5 p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 p-5"><SectionTitle className="mb-0">Nearby mandis <Pill tone="gray">{selectedCommodity?.name_en || 'Select a crop'} · INR/quintal</Pill></SectionTitle><span className="text-[10px] text-muted">{filters.district || filters.state || 'Choose a state to load prices'}</span></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[690px] text-left"><thead className="bg-[#fafbf9] text-[9px] font-bold uppercase tracking-wider text-[#9aa69c]"><tr><th className="px-5 py-3">Market</th><th className="px-4 py-3">Modal price</th><th className="px-4 py-3">Price range</th><th className="px-4 py-3">Distance</th><th className="px-4 py-3">Price date</th><th className="px-5 py-3">Source</th></tr></thead><tbody className="divide-y divide-[#eff2ec]">
        {sortedPrices.map((price, index) => <tr key={`${price.provider_key}-${price.price_date}-${index}`} className={price.mandi_id === selectedMandiId ? 'bg-leaf-50/40' : ''}><td className="px-5 py-4"><button type="button" onClick={() => price.mandi_id && setSelectedMandiId(price.mandi_id)} className="text-left"><p className="text-xs font-bold text-ink">{price.market_name}</p><p className="mt-0.5 text-[10px] text-muted">{price.district || price.state}</p></button></td><td className="px-4 py-4 text-xs font-extrabold text-ink">{rupees(price.modal_price)}</td><td className="px-4 py-4 text-[10px] text-muted">{rupees(price.min_price)} – {rupees(price.max_price)}</td><td className="px-4 py-4 text-xs text-muted">{price.distance == null ? '—' : `${price.distance.toFixed(1)} km`}</td><td className="px-4 py-4 text-xs text-muted">{displayDate(price.price_date)}</td><td className="px-5 py-4"><Pill tone={statusTone[marketData?.source_status] || 'gray'}>{sourceLabel(marketData?.source_status)}</Pill></td></tr>)}
        {!sortedPrices.length && <tr><td colSpan="6" className="px-5 py-8 text-center text-xs text-muted">Mandi quotes will appear here after you load prices.</td></tr>}
      </tbody></table></div>
      <div className="border-t border-[#eff2ec] px-5 py-3 text-[10px] leading-5 text-muted">Distances are straight-line display estimates. They appear when your location and mandi coordinates are available. Prices reflect the observation date shown.</div>
    </Card>
  </>
}
