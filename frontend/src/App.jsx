import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import { Card } from './components/ui'

const Home = lazy(() => import('./pages/Home'))
const ReportProblem = lazy(() => import('./pages/ReportProblem'))
const CropResult = lazy(() => import('./pages/CropResult'))
const MyCrops = lazy(() => import('./pages/MyCrops'))
const NearbyAlerts = lazy(() => import('./pages/NearbyAlerts'))
const MyReports = lazy(() => import('./pages/MyReports'))
const MarketIntelligence = lazy(() => import('./pages/MarketIntelligence'))
const SeedFertilizer = lazy(() => import('./pages/SeedFertilizer'))
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'))

function PageLoader() { return <Card className="animate-pulse"><div className="h-3 w-24 rounded bg-[#e8eee4]" /><div className="mt-4 h-8 w-64 rounded bg-[#e8eee4]" /><div className="mt-6 h-40 rounded-xl bg-[#f1f4ed]" /></Card> }

export default function App() {
  return <Suspense fallback={<div className="p-6"><PageLoader /></div>}><Routes><Route element={<AppShell />}>
    <Route index element={<Home />} />
    <Route path="report" element={<ReportProblem />} />
    <Route path="reports/:id" element={<CropResult />} />
    <Route path="crops" element={<MyCrops />} />
    <Route path="alerts" element={<NearbyAlerts />} />
    <Route path="reports" element={<MyReports />} />
    <Route path="market" element={<MarketIntelligence />} />
    <Route path="farm" element={<SeedFertilizer />} />
    <Route path="admin" element={<AdminDashboard />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Route></Routes></Suspense>
}
