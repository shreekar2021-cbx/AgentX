import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Camera, Check, CloudSun, FileImage, ImagePlus, Info, MapPin, Mic, ShieldCheck, Sparkles, Sprout, UploadCloud, X } from 'lucide-react'
import { api, ApiRequestError } from '../../lib/api'
import { queueReport } from '../../lib/offlineQueue'
import { createVoiceSession, voiceAvailable, type VoiceSession } from '../../lib/voice'
import { useTranslation } from '../../lib/i18n'
import { demoFarm } from '../../lib/demo'
import { PageHeader, Panel } from '../../components/UI'

const fallbackCrops = ['Paddy', 'Cotton', 'Maize', 'Chilli', 'Tomato', 'Groundnut', 'Red gram', 'Green gram', 'Black gram', 'Soybean', 'Turmeric', 'Onion', 'Potato', 'Wheat', 'Sorghum', 'Pearl millet', 'Brinjal', 'Okra']
const stages = [
  { key: 'validated', label: 'Image validated', icon: FileImage },
  { key: 'weather', label: 'Weather context', icon: CloudSun },
  { key: 'crop_health', label: 'Crop health', icon: Sprout },
  { key: 'nearby', label: 'Nearby reports', icon: MapPin },
  { key: 'risk', label: 'Risk assessment', icon: ShieldCheck },
  { key: 'outbreak', label: 'Cluster check', icon: Sparkles },
  { key: 'persist', label: 'Save result', icon: Check },
]

export default function ReportProblem() {
  const navigate = useNavigate()
  const { language, t } = useTranslation()
  const cropQuery = useQuery({ queryKey: ['knowledge-crops'], queryFn: api.knowledgeCrops, retry: false, networkMode: 'always' })
  const health = useQuery({ queryKey: ['health'], queryFn: api.health, retry: false })
  const [crop, setCrop] = useState('Cotton')
  const [field, setField] = useState('North Field')
  const [district, setDistrict] = useState(demoFarm.district)
  const [latitude, setLatitude] = useState(String(demoFarm.coordinates[0]))
  const [longitude, setLongitude] = useState(String(demoFarm.coordinates[1]))
  const [description, setDescription] = useState('')
  const [notes, setNotes] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [demoSample, setDemoSample] = useState(false)
  const [preview, setPreview] = useState<string | null>(null)
  const [stage, setStage] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [locationMessage, setLocationMessage] = useState('')
  const [pendingReportId, setPendingReportId] = useState<string | null>(null)
  const [pendingFingerprint, setPendingFingerprint] = useState<string | null>(null)
  const [pendingMutationId, setPendingMutationId] = useState<string | null>(null)
  const [transcript, setTranscript] = useState('')
  const [recording, setRecording] = useState(false)
  const voiceSession = useRef<VoiceSession | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)
  const cameraInput = useRef<HTMLInputElement>(null)
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview) }, [preview])
  useEffect(() => () => voiceSession.current?.stop(), [])

  function toggleVoice() {
    if (recording) { voiceSession.current?.stop(); setRecording(false); return }
    const code = language === 'te' ? 'te-IN' : language === 'hi' ? 'hi-IN' : 'en-IN'
    const session = createVoiceSession(code, { onText: setTranscript, onError: setError, onEnd: () => setRecording(false) })
    if (!session) { setError('Speech input is unavailable in this browser. You can type the symptoms.'); return }
    voiceSession.current = session
    setTranscript(''); setRecording(true); setError('')
    try { session.start() } catch { setRecording(false); setError('Microphone access was unavailable. You can type the symptoms.') }
  }

  function selectFile(candidate?: File, synthetic = false) {
    if (!candidate) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(candidate.type)) { setError('Choose a JPG, PNG, or WebP image.'); return }
    if (candidate.size > 10 * 1024 * 1024) { setError('Image must be under 10 MB.'); return }
    setFile(candidate); setDemoSample(synthetic); setPreview(URL.createObjectURL(candidate)); setError('')
  }
  async function loadDemoPhoto() {
    try {
      const response = await fetch('/demo/cotton-whitefly-synthetic.png')
      if (!response.ok) throw new Error('Sample image unavailable.')
      selectFile(new File([await response.blob()], 'cotton-whitefly-synthetic.png', { type: 'image/png' }), true)
    } catch { setError('Synthetic sample image is unavailable. Choose your own JPG, PNG, or WebP image.') }
  }
  function useLocation() {
    if (!navigator.geolocation) { setLocationMessage('Browser location is unavailable. Enter coordinates manually.'); return }
    navigator.geolocation.getCurrentPosition(position => {
      setLatitude(position.coords.latitude.toFixed(6)); setLongitude(position.coords.longitude.toFixed(6)); setLocationMessage('Browser location selected. Confirm the district before submitting.')
    }, () => setLocationMessage('Location permission was unavailable. Enter coordinates manually.'), { enableHighAccuracy: false, timeout: 10000 })
  }
  async function submit() {
    if (!file || description.trim().length < 10) { setError('Add a crop image and at least 10 characters describing symptoms.'); return }
    const lat = Number(latitude), lon = Number(longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) { setError('Enter valid latitude and longitude.'); return }
    const fingerprint = JSON.stringify([crop, field, district, latitude, longitude, description.trim(), notes.trim(), file.name, file.size, file.lastModified, demoSample])
    const mutationId = pendingFingerprint === fingerprint && pendingMutationId ? pendingMutationId : crypto.randomUUID()
    setBusy(true); setError(''); setStage('')
    let reportId = pendingFingerprint === fingerprint ? pendingReportId : null
    try {
      if (!navigator.onLine) {
        await queueReport({ id: mutationId, crop, field, district, symptoms: description.trim(), notes: notes.trim(), latitude, longitude, image: file, imageName: file.name, imageType: file.type, demoSample, serverId: reportId ?? undefined })
        navigate('/reports'); return
      }
      if (!reportId) {
        const form = new FormData()
        form.set('crop', crop); form.set('field', field); form.set('district', district)
        form.set('symptoms', description.trim()); form.set('notes', notes.trim())
        form.set('latitude', latitude); form.set('longitude', longitude); form.set('image', file); form.set('client_mutation_id', mutationId); form.set('demo_sample', String(demoSample))
        const created = await api.createReport(form)
        reportId = created.id
        setPendingReportId(reportId)
        setPendingFingerprint(fingerprint)
        setPendingMutationId(mutationId)
        setStage('validated')
      }
      await api.streamAnalysis(reportId, event => setStage(event.stage))
      navigate(`/result/${reportId}`)
    } catch (caught) {
      if (reportId || (caught instanceof ApiRequestError && caught.status === 0)) {
        try {
          await queueReport({ id: mutationId, crop, field, district, symptoms: description.trim(), notes: notes.trim(), latitude, longitude, image: file, imageName: file.name, imageType: file.type, demoSample, serverId: reportId ?? undefined })
          navigate('/reports'); return
        } catch (storageError) { setError(`Report could not be saved offline: ${storageError instanceof Error ? storageError.message : 'storage error'}`) }
      } else setError(caught instanceof Error ? caught.message : 'Report analysis failed. You can retry the saved report.')
    }
    finally { setBusy(false) }
  }
  const cropOptions = cropQuery.data?.crops.map(item => item.name) ?? fallbackCrops
  const currentFingerprint = JSON.stringify([crop, field, district, latitude, longitude, description.trim(), notes.trim(), file?.name, file?.size, file?.lastModified, demoSample])
  const currentIndex = stages.findIndex(item => item.key === stage)
  return <div className="page"><PageHeader eyebrow="FIELD OBSERVATION / NEW REPORT" title={t('reportTitle')} description={t('reportIntro')} action={cropQuery.data?.source.includes('OFFLINE') && <span className="source-badge source-fallback">CURATED OFFLINE CROP LIST</span>}/><div className="report-layout"><div className="report-form">
    <Panel className="form-panel"><div className="step-heading"><span>01</span><div><h2>Tell us about the crop</h2><p>Choose the crop and field you are observing.</p></div></div><div className="form-grid"><label className="field-label">Crop<select value={crop} onChange={event => setCrop(event.target.value)}>{cropOptions.map(item => <option key={item}>{item}</option>)}</select></label><label className="field-label">Field<input className="text-input" value={field} maxLength={120} onChange={event => setField(event.target.value)}/></label></div><div className="form-grid location-fields"><label className="field-label">District<input className="text-input" value={district} maxLength={80} onChange={event => setDistrict(event.target.value)}/></label><button className="button secondary location-button" onClick={useLocation}><MapPin size={16}/> Use browser location</button><label className="field-label">Latitude<input className="text-input" inputMode="decimal" value={latitude} onChange={event => setLatitude(event.target.value)}/></label><label className="field-label">Longitude<input className="text-input" inputMode="decimal" value={longitude} onChange={event => setLongitude(event.target.value)}/></label></div>{locationMessage && <div className="location-message">{locationMessage}</div>}</Panel>
    <Panel className="form-panel"><div className="step-heading"><span>02</span><div><h2>Show us the problem</h2><p>Upload a clear photo of the affected part.</p></div></div><input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={event => selectFile(event.target.files?.[0])}/><input ref={cameraInput} type="file" accept="image/*" capture="environment" hidden onChange={event => selectFile(event.target.files?.[0])}/>{preview ? <div className="image-preview"><img src={preview} alt="Selected crop observation"/><button onClick={() => { setPreview(null); setFile(null); setDemoSample(false) }} aria-label="Remove image"><X size={18}/></button></div> : <div className="upload-zone" role="button" tabIndex={0} aria-label="Choose a crop photo or drop one here" onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); fileInput.current?.click() } }} onClick={() => fileInput.current?.click()} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); selectFile(event.dataTransfer.files[0]) }}><div className="upload-icon"><ImagePlus size={27}/></div><strong>Drop your crop photo here</strong><p>or click to browse your files</p><small>JPG, PNG or WebP · up to 10 MB</small></div>}{health.data?.demo_mode && <div className="p4-sample-photo"><span>{demoSample ? "Synthetic sample selected. This report will be labelled synthetic." : "Need a demo image? Use the generated synthetic cotton sample."}</span><button className="button secondary" onClick={loadDemoPhoto}>Load synthetic sample</button></div>}<div className="upload-actions"><button className="button secondary" onClick={() => fileInput.current?.click()}><UploadCloud size={17}/> Upload image</button><button className="button secondary" onClick={() => cameraInput.current?.click()}><Camera size={17}/> Use camera</button></div></Panel>
    <Panel className="form-panel"><div className="step-heading"><span>03</span><div><h2>{t('symptomsHeading')}</h2><p>Describe symptoms as they appear, without guessing a diagnosis.</p></div></div><label className="field-label">{t('symptoms')} <span className="required">*</span><textarea rows={4} value={description} onChange={event => setDescription(event.target.value)} placeholder="e.g. Yellow spots on lower leaves, curled edges, insects under leaves..."/></label><button className="voice-button" onClick={toggleVoice} disabled={!voiceAvailable()}><Mic size={17}/> {recording ? 'Stop recording' : t('voice')} <span>{voiceAvailable() ? (recording ? 'LISTENING' : language.toUpperCase()) : 'UNAVAILABLE'}</span></button>{transcript && <div className="p3-transcript"><label className="field-label">{t('transcript')}<textarea rows={3} value={transcript} onChange={event => setTranscript(event.target.value)}/></label><button className="button secondary" onClick={() => { setDescription(current => `${current} ${transcript}`.trim()); setTranscript('') }}>{t('confirmVoice')}</button></div>}<p className="p3-voice-note">Speech availability depends on your browser and may send audio to its recognition service. Review text before adding it.</p><label className="field-label notes-label">{t('notes')} <span className="optional">(optional)</span><textarea rows={3} value={notes} onChange={event => setNotes(event.target.value)} placeholder="When did it begin? Has it spread? Any recent treatment?"/></label></Panel>
    {error && <div className="form-error" role="alert"><Info size={16}/>{error}</div>}<button className="button primary submit-button" disabled={busy} onClick={submit}>{busy ? t('analyzing') : pendingReportId && pendingFingerprint === currentFingerprint ? t('retry') : t('submit')} <ArrowRight size={18}/></button><p className="form-fineprint">Offline reports are saved in this browser until synchronization. The image and field description may be sent to Mistral when configured.</p>
  </div><aside className="report-aside"><Panel className="pipeline-card"><div className="aside-title"><span className="pipeline-symbol"><Sparkles size={18}/></span><div><strong>Analysis journey</strong><span>{busy ? 'Live pipeline progress' : 'Stages run after submission'}</span></div></div><div className="pipeline-list">{stages.map((item, index) => <div className={`pipeline-step ${currentIndex > index || stage === 'complete' || stage === 'result' ? 'done' : currentIndex === index ? 'running' : ''}`} key={item.key}><div className="pipeline-node">{currentIndex > index || stage === 'complete' || stage === 'result' ? <Check size={17}/> : <item.icon size={17}/>}</div><span>{item.label}</span><small>0{index + 1}</small></div>)}</div><div className="pipeline-note"><Info size={15}/> Each highlighted stage reflects a backend event. A failed provider switches to a labelled fallback.</div></Panel><Panel className="tip-card"><div className="tip-icon"><Camera size={19}/></div><strong>For a clearer photo</strong><p>Use natural light, focus on affected leaves, and include enough field context for an expert to review.</p></Panel></aside></div></div>
}
