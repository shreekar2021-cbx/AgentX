export const farmer = { name: 'Ravi Kumar', location: 'Warangal, Telangana', farm: 'Green Valley Farm', avatar: 'RK' }

export const crops = [
  { id: 'c1', name: 'Tomato', variety: 'Arka Rakshak', season: 'Kharif', stage: 'Flowering', progress: 68, area: '2.5 acres', health: 'Good', color: 'tomato' },
  { id: 'c2', name: 'Rice', variety: 'Swarna', season: 'Kharif', stage: 'Tillering', progress: 42, area: '4 acres', health: 'Watch', color: 'rice' },
  { id: 'c3', name: 'Chilli', variety: 'Teja S17', season: 'Kharif', stage: 'Vegetative', progress: 31, area: '1.5 acres', health: 'Good', color: 'chilli' },
]

export const reports = [
  { id: 'RPT-2408', crop: 'Tomato', issue: 'Brown spots on lower leaves', diagnosis: 'Early blight', confidence: 89, severity: 'Medium', status: 'Reviewed', date: 'Today, 9:42 AM', icon: '🍅' },
  { id: 'RPT-2396', crop: 'Rice', issue: 'Pale yellow leaf tips', diagnosis: 'Possible nutrient deficiency', confidence: 76, severity: 'Low', status: 'Monitoring', date: 'Yesterday', icon: '🌾' },
  { id: 'RPT-2371', crop: 'Chilli', issue: 'Small holes in new leaves', diagnosis: 'Leaf-eating caterpillar', confidence: 93, severity: 'High', status: 'Action needed', date: 'Sep 21', icon: '🌶️' },
  { id: 'RPT-2312', crop: 'Tomato', issue: 'Leaves curling inward', diagnosis: 'Possible whitefly activity', confidence: 81, severity: 'Medium', status: 'Resolved', date: 'Sep 18', icon: '🍅' },
]

export const alerts = [
  { crop: 'Tomato', disease: 'Early blight activity', district: 'Hanamkonda', distance: '3.2 km', reports: 8, severity: 'High', time: '2 hours ago', icon: '🍅' },
  { crop: 'Rice', disease: 'Leaf folder sightings', district: 'Parkal', distance: '7.8 km', reports: 4, severity: 'Medium', time: 'Yesterday', icon: '🌾' },
  { crop: 'Cotton', disease: 'Pink bollworm watch', district: 'Narsampet', distance: '12.4 km', reports: 3, severity: 'Medium', time: '2 days ago', icon: '☁️' },
]

export const marketPrices = [
  { market: 'Warangal APMC', district: 'Warangal', min: 2100, max: 2850, modal: 2480, change: 4.2, distance: 8.4, freshness: 'Today' },
  { market: 'Enumamula Market', district: 'Warangal', min: 2250, max: 2920, modal: 2610, change: 7.8, distance: 11.2, freshness: 'Today' },
  { market: 'Karimnagar APMC', district: 'Karimnagar', min: 1980, max: 2680, modal: 2310, change: -2.1, distance: 52.6, freshness: 'Yesterday' },
  { market: 'Hyderabad Market Yard', district: 'Hyderabad', min: 2400, max: 3100, modal: 2790, change: 3.4, distance: 146, freshness: 'Today' },
]

export const priceHistory = [
  { date: 'Sep 01', price: 2180 }, { date: 'Sep 04', price: 2240 }, { date: 'Sep 07', price: 2190 },
  { date: 'Sep 10', price: 2320 }, { date: 'Sep 13', price: 2280 }, { date: 'Sep 16', price: 2390 },
  { date: 'Sep 19', price: 2360 }, { date: 'Sep 22', price: 2510 }, { date: 'Sep 25', price: 2480 },
]

export const seedRecommendations = [
  { name: 'Arka Rakshak', type: 'Hybrid', yield: '35–40 t/ha', maturity: '140–150 days', reason: 'Strong resistance to bacterial wilt and tomato leaf curl virus.', score: 96, tag: 'Best match' },
  { name: 'US-440', type: 'Hybrid', yield: '30–35 t/ha', maturity: '125–135 days', reason: 'Performs well in warm conditions with moderate irrigation.', score: 88, tag: 'Heat tolerant' },
  { name: 'Pusa Ruby', type: 'Open pollinated', yield: '20–25 t/ha', maturity: '120–130 days', reason: 'Reliable option for local markets and staggered harvest.', score: 81, tag: 'Good value' },
]

export const weeklyRain = [
  { day: 'Mon', rain: 0 }, { day: 'Tue', rain: 2 }, { day: 'Wed', rain: 0 }, { day: 'Thu', rain: 8 },
  { day: 'Fri', rain: 0 }, { day: 'Sat', rain: 1 }, { day: 'Sun', rain: 0 },
]
