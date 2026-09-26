import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { MapPin, Save, Sprout } from 'lucide-react'
import { api } from '../../lib/api'
import { useTranslation } from '../../lib/i18n'
import type { FarmProfile, FarmProfileInput } from '../../lib/types'
import { EmptyState, PageHeader, Panel, SectionHead, Skeleton } from '../../components/UI'

const textFields: [keyof FarmProfileInput, string][] = [['farm_name', 'farmName'], ['village', 'village'], ['district', 'district'], ['crop', 'currentCrop'], ['season', 'season'], ['soil_type', 'soilType'], ['previous_crop', 'previousCrop'], ['irrigation', 'irrigation']]
const numberFields: [keyof FarmProfileInput, string][] = [['latitude', 'latitude'], ['longitude', 'longitude'], ['area_acres', 'farmArea'], ['soil_ph', 'soilPH'], ['nitrogen_kg_ha', 'nitrogen'], ['phosphorus_kg_ha', 'phosphorus'], ['potassium_kg_ha', 'potassium'], ['budget_inr', 'budget']]
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
  return <><div className="p3-profile-grid"><Panel><SectionHead title={t('farmAndCrop')}/><div className="p3-form-grid">{textFields.map(([key, label]) => <label key={key}>{t(label as any)}<input className="text-input" value={textValue(key)} onChange={event => setText(key, event.target.value)}/></label>)}<label>{t('plantingDate')}<input className="text-input" type="date" value={values.planting_date ?? ''} onChange={event => setText('planting_date', event.target.value)}/></label></div></Panel><Panel><SectionHead title={t('locationAndSoil')}/><button className="button secondary" onClick={useLocation}><MapPin size={16}/> {t('useLocation')}</button><div className="p3-form-grid">{numberFields.map(([key, label]) => <label key={key}>{t(label as any)}<input className="text-input" type="number" step="any" value={textValue(key)} onChange={event => setNumber(key, event.target.value)} placeholder="Unknown"/></label>)}</div><p className="p2-attribution">Leave unknown values empty. N, P, K values use kg/ha only when your laboratory reports that unit.</p></Panel></div><Panel className="p3-profile-lab"><SectionHead title={t('soilLabInterpretation')}/><p>{t('soilLabDesc')}</p><div className="p3-form-grid">{nutrients.map(nutrient => <label key={nutrient}>{nutrient} {t('labCategory')}<select value={values.lab_status?.[nutrient] ?? ''} onChange={event => setValues(current => { const lab_status = { ...current.lab_status }; if (event.target.value === '') delete lab_status[nutrient]; else lab_status[nutrient] = event.target.value as 'low' | 'adequate' | 'high'; return { ...current, lab_status } })}><option value="">{t('notSupplied')}</option><option value="low">{t('low')}</option><option value="adequate">{t('adequate')}</option><option value="high">{t('high')}</option></select></label>)}</div><div className="p3-form-grid">{['Zinc', 'Iron', 'Boron'].map(nutrient => <label key={nutrient}>{nutrient} {t('measuredValue')}<input className="text-input" type="number" step="any" placeholder="Unknown; include lab unit in records" value={values.micronutrients?.[nutrient] ?? ''} onChange={event => setValues(current => { const micronutrients = { ...current.micronutrients }; if (event.target.value === '') delete micronutrients[nutrient]; else micronutrients[nutrient] = Number(event.target.value); return { ...current, micronutrients } })}/></label>)}</div></Panel>{error && <div className="form-error" role="alert">{error}</div>}{saved && <p className="p3-success" role="status">{saved}</p>}<div className="p3-actions"><button className="button primary" disabled={saving} onClick={save}><Save size={17}/>{saving ? t('saving') : t('save')}</button><Link className="button secondary" to="/recommendations"><Sprout size={17}/> {t('viewGuidance')}</Link></div></>
}

export default function FarmProfilePage() {
  const { t } = useTranslation()
  const query = useQuery({ queryKey: ['farm-profile'], queryFn: api.farmProfile })
  return <div className="page"><PageHeader eyebrow="YOUR FARM / PROFILE" title={t('farmTitle')} description={t('farmDescription')}/> {query.data?.is_synthetic && <div className="demo-notice">This sample farm and soil profile is synthetic. Replace it with verified field and laboratory data.</div>}{query.isPending ? <Skeleton className="result-loading"/> : query.isError ? <EmptyState title={t('profileUnavailable')} body={query.error.message} action={<button className="button secondary" onClick={() => query.refetch()}>{t('retry')}</button>}/> : <ProfileEditor key={query.data?.updated_at ?? 'empty'} initial={query.data}/>}</div>
}
