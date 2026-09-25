import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { MapPin, Save, Sprout } from 'lucide-react'
import { api } from '../../lib/api'
import { useTranslation } from '../../lib/i18n'
import type { FarmProfile, FarmProfileInput } from '../../lib/types'
import { EmptyState, PageHeader, Panel, SectionHead, Skeleton } from '../../components/UI'

const textFields: [keyof FarmProfileInput, string][] = [['farm_name', 'Farm name'], ['village', 'Village'], ['district', 'District'], ['crop', 'Current crop'], ['season', 'Season'], ['soil_type', 'Soil type'], ['previous_crop', 'Previous crop'], ['irrigation', 'Irrigation']]
const numberFields: [keyof FarmProfileInput, string][] = [['latitude', 'Latitude'], ['longitude', 'Longitude'], ['area_acres', 'Farm area (acres)'], ['soil_ph', 'Soil pH'], ['nitrogen_kg_ha', 'Nitrogen (kg/ha)'], ['phosphorus_kg_ha', 'Phosphorus (kg/ha)'], ['potassium_kg_ha', 'Potassium (kg/ha)'], ['budget_inr', 'Budget (₹)']]
const nutrients = ['N', 'P', 'K', 'Zinc', 'Iron', 'Boron']

function ProfileEditor({ initial }: { initial: FarmProfile | null }) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [values, setValues] = useState<FarmProfileInput>(initial ?? {})
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')
  const [saving, setSaving] = useState(false)
  const textValue = (key: keyof FarmProfileInput) => String(values[key] ?? '')
  function setText(key: keyof FarmProfileInput, value: string) { setValues(current => ({ ...current, [key]: value || null })) }
  function setNumber(key: keyof FarmProfileInput, value: string) { setValues(current => ({ ...current, [key]: value === '' ? null : Number(value) })) }
  function useLocation() { navigator.geolocation?.getCurrentPosition(position => setValues(current => ({ ...current, latitude: Number(position.coords.latitude.toFixed(6)), longitude: Number(position.coords.longitude.toFixed(6)) })), () => setError('Browser location unavailable. Enter coordinates manually.')) }
  async function save() { setSaving(true); setError(''); try { const result = await api.saveFarmProfile(values); await queryClient.invalidateQueries({ queryKey: ['farm-profile'] }); setSaved(`Saved ${new Date(result.updated_at).toLocaleString('en-IN')}`) } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not save profile.') } finally { setSaving(false) } }
  return <><div className="p3-profile-grid"><Panel><SectionHead title="Farm and crop"/><div className="p3-form-grid">{textFields.map(([key, label]) => <label key={key}>{label}<input className="text-input" value={textValue(key)} onChange={event => setText(key, event.target.value)}/></label>)}<label>Planting date<input className="text-input" type="date" value={values.planting_date ?? ''} onChange={event => setText('planting_date', event.target.value)}/></label></div></Panel><Panel><SectionHead title="Location and soil measurements"/><button className="button secondary" onClick={useLocation}><MapPin size={16}/> Use browser location</button><div className="p3-form-grid">{numberFields.map(([key, label]) => <label key={key}>{label}<input className="text-input" type="number" step="any" value={textValue(key)} onChange={event => setNumber(key, event.target.value)} placeholder="Unknown"/></label>)}</div><p className="p2-attribution">Leave unknown values empty. N, P, K values use kg/ha only when your laboratory reports that unit.</p></Panel></div><Panel className="p3-profile-lab"><SectionHead title="Soil laboratory interpretation"/><p>Optional lab categories guide nutrient priorities. Raw numbers alone are never treated as low or high.</p><div className="p3-form-grid">{nutrients.map(nutrient => <label key={nutrient}>{nutrient} lab category<select value={values.lab_status?.[nutrient] ?? ''} onChange={event => setValues(current => { const lab_status = { ...current.lab_status }; if (event.target.value === '') delete lab_status[nutrient]; else lab_status[nutrient] = event.target.value as 'low' | 'adequate' | 'high'; return { ...current, lab_status } })}><option value="">Not supplied</option><option value="low">Low</option><option value="adequate">Adequate</option><option value="high">High</option></select></label>)}</div><div className="p3-form-grid">{['Zinc', 'Iron', 'Boron'].map(nutrient => <label key={nutrient}>{nutrient} measured value<input className="text-input" type="number" step="any" placeholder="Unknown; include lab unit in records" value={values.micronutrients?.[nutrient] ?? ''} onChange={event => setValues(current => { const micronutrients = { ...current.micronutrients }; if (event.target.value === '') delete micronutrients[nutrient]; else micronutrients[nutrient] = Number(event.target.value); return { ...current, micronutrients } })}/></label>)}</div></Panel>{error && <div className="form-error" role="alert">{error}</div>}{saved && <p className="p3-success" role="status">{saved}</p>}<div className="p3-actions"><button className="button primary" disabled={saving} onClick={save}><Save size={17}/>{saving ? 'Saving...' : t('save')}</button><Link className="button secondary" to="/recommendations"><Sprout size={17}/> View guidance</Link></div></>
}

export default function FarmProfilePage() {
  const { t } = useTranslation()
  const query = useQuery({ queryKey: ['farm-profile'], queryFn: api.farmProfile })
  return <div className="page"><PageHeader eyebrow="YOUR FARM / PROFILE" title={t('farmTitle')} description="Store only measurements and details you know. Missing values stay unknown."/> {query.data?.is_synthetic && <div className="demo-notice">This sample farm and soil profile is synthetic. Replace it with verified field and laboratory data.</div>}{query.isPending ? <Skeleton className="result-loading"/> : query.isError ? <EmptyState title="Profile unavailable" body={query.error.message} action={<button className="button secondary" onClick={() => query.refetch()}>Retry</button>}/> : <ProfileEditor key={query.data?.updated_at ?? 'empty'} initial={query.data}/>}</div>
}
