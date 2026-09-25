import type { Alert, Crop, Mandi, Report } from './types'
export const demoFarm = { name: 'Green Valley Farm', owner: 'Ravi Kumar', village: 'Shamshabad', district: 'Rangareddy', area: 12.4, coordinates: [17.2517, 78.3893] as [number, number] }
export const crops: Crop[] = [
  { id: 'cotton', name: 'Cotton', variety: 'RCH 659', area: 5.2, stage: 'Flowering', health: 92, planted: '18 Jun 2026', accent: '#a6dec5' },
  { id: 'paddy', name: 'Paddy', variety: 'MTU 1010', area: 4.1, stage: 'Tillering', health: 86, planted: '02 Jul 2026', accent: '#dbc48a' },
  { id: 'maize', name: 'Maize', variety: 'DHM 117', area: 3.1, stage: 'Vegetative', health: 95, planted: '25 Jun 2026', accent: '#a7bdec' },
]
export const alerts: Alert[] = [
  { id: 'a1', crop: 'Cotton', title: 'Whitefly activity reported', district: 'Rangareddy', distance: 4.8, severity: 'Moderate', time: '2 hours ago', lat: 17.286, lng: 78.415, radius: 2.3, description: 'Several demo observations near adjacent cotton fields. Inspect the undersides of leaves during the next field walk.' },
  { id: 'a2', crop: 'Paddy', title: 'Leaf blast watch', district: 'Medchal', distance: 12.6, severity: 'High', time: '6 hours ago', lat: 17.351, lng: 78.474, radius: 3.5, description: 'Illustrative cluster of leaf blast symptoms. Monitor low lying plots after humid mornings.' },
  { id: 'a3', crop: 'Cotton', title: 'Pink bollworm sightings', district: 'Rangareddy', distance: 18.2, severity: 'Low', time: 'Yesterday', lat: 17.156, lng: 78.29, radius: 1.7, description: 'Illustrative pheromone trap observations. Keep routine scouting records.' },
  { id: 'a4', crop: 'Maize', title: 'Fall armyworm watch', district: 'Vikarabad', distance: 25.4, severity: 'Moderate', time: 'Yesterday', lat: 17.39, lng: 78.18, radius: 2.4, description: 'Illustrative nearby report. Check whorls and note fresh feeding damage.' },
]
export const reports: Report[] = [
  { id: 'AGR-2408', crop: 'Cotton', title: 'Leaf discoloration', date: '24 Sep 2026', status: 'Demo result', severity: 'Moderate', field: 'North Field' },
  { id: 'AGR-2407', crop: 'Paddy', title: 'Brown spots on leaves', date: '22 Sep 2026', status: 'Demo result', severity: 'Low', field: 'East Plot' },
  { id: 'AGR-2406', crop: 'Maize', title: 'Stunted growth', date: '20 Sep 2026', status: 'Waiting to sync', severity: 'Low', field: 'South Field' },
]
export const mandis: Mandi[] = [
  { name: 'Hyderabad', district: 'Rangareddy', distance: 24, price: 7280, min: 6940, max: 7510, change: 2.8 },
  { name: 'Mahbubnagar', district: 'Mahbubnagar', distance: 68, price: 7140, min: 6820, max: 7390, change: 1.2 },
  { name: 'Sangareddy', district: 'Sangareddy', distance: 79, price: 7390, min: 7010, max: 7610, change: -0.6 },
  { name: 'Warangal', district: 'Warangal', distance: 142, price: 7210, min: 6950, max: 7440, change: 1.8 },
]
export const commodities = ['Cotton', 'Paddy', 'Maize', 'Red gram']
export const priceMultipliers: Record<string, number> = { Cotton: 1, Paddy: .32, Maize: .29, 'Red gram': 1.18 }
export const chart30 = [64, 62, 66, 63, 69, 68, 67, 73, 71, 70, 75, 72, 78, 77, 75, 79, 78, 82, 80, 83, 81, 86, 84, 85, 88, 87, 91, 89, 92, 94].map((value, i) => ({ day: i + 1, value }))
export const chart7 = chart30.slice(-7)
