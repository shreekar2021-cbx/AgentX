import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { CloudOff, ExternalLink, Languages, RefreshCw, ShieldCheck, Sparkles, Volume2, VolumeX } from 'lucide-react'
import { useUI } from '../../lib/store'
import { useTranslation } from '../../lib/i18n'
import { useQueueStatus } from '../../lib/useQueueStatus'
import { PageHeader, Panel, SectionHead } from '../../components/UI'
import { api } from '../../lib/api'
import { speakText, speechAvailable, stopSpeaking } from '../../lib/voice'

export default function SettingsPage() {
  const { language, setLanguage } = useUI()
  const { t } = useTranslation()
  const queue = useQueueStatus()
  const voiceStatus = useQuery({ queryKey: ['voice-status'], queryFn: api.voiceStatus, retry: false })
  const [testingVoice, setTestingVoice] = useState(false)

  function testVoicePlayback() {
    if (testingVoice) {
      stopSpeaking()
      setTestingVoice(false)
      return
    }
    const sampleText =
      language === 'te'
        ? 'నమస్కారం రైతు సోదరా. అగ్రివిజన్ వాయిస్ అసిస్టెంట్ మరియు గ్రోక్ అనువాదం సిద్ధంగా ఉన్నాయి.'
        : language === 'hi'
        ? 'नमस्ते किसान मित्र। एग्रीविज़न वॉइस असिस्टेंट और ग्रोक अनुवाद तैयार हैं।'
        : 'Hello farmer. AgriVision voice assistant and Groq translation are ready.'
    setTestingVoice(true)
    speakText(sampleText, language, {
      onEnd: () => setTestingVoice(false),
      onError: () => setTestingVoice(false),
    })
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow={t('fieldIntelligenceOverview')}
        title={t('settings')}
        description={t('settingsDescription')}
      />

      <div className="p3-profile-grid">
        {/* Language Selection */}
        <Panel>
          <SectionHead title={t('language')} />
          <div className="p3-settings-symbol">
            <Languages size={22} />
          </div>
          <label className="field-label">
            {t('chooseLanguage')}
            <select
              value={language}
              onChange={event => setLanguage(event.target.value as 'en' | 'te' | 'hi')}
            >
              <option value="en">{t('langEnglish')}</option>
              <option value="te">{t('langTelugu')}</option>
              <option value="hi">{t('langHindi')}</option>
            </select>
          </label>
          <p>{t('languageNote')}</p>
        </Panel>

        {/* Connectivity */}
        <Panel>
          <SectionHead title={t('connectivityTitle')} />
          <div className="p3-settings-symbol">
            <CloudOff size={22} />
          </div>
          <div className="admin-line">
            <span>{t('connection')}</span>
            <strong>{queue.online ? t('online') : t('offline')}</strong>
          </div>
          <div className="admin-line">
            <span>{t('reportsOnDevice')}</span>
            <strong>{queue.count} {t('waitingSync')}</strong>
          </div>
          <p>{t('connectivityNote')}</p>
          <Link to="/reports" className="button secondary">
            <RefreshCw size={16} />
            {t('syncNow')}
          </Link>
        </Panel>

        {/* Groq AI & Voice Assistant */}
        <Panel>
          <SectionHead title={t('groqAiSettings')} />
          <div className="p3-settings-symbol">
            <Sparkles size={22} />
          </div>
          <div className="admin-line">
            <span>Status</span>
            <strong style={{ color: voiceStatus.data?.groq_configured ? '#16a34a' : '#ea580c' }}>
              {voiceStatus.data?.groq_configured ? t('groqConnected') : t('groqNotConfigured')}
            </strong>
          </div>
          <div className="admin-line">
            <span>{t('groqModel')}</span>
            <strong>{voiceStatus.data?.groq_model ?? 'llama-3.3-70b-versatile'}</strong>
          </div>
          <div className="admin-line">
            <span>Fast Translator</span>
            <strong>{voiceStatus.data?.groq_fast_model ?? 'llama-3.1-8b-instant'}</strong>
          </div>
          <div className="admin-line">
            <span>Active Provider</span>
            <strong style={{ textTransform: 'uppercase' }}>{voiceStatus.data?.active_provider ?? 'local'}</strong>
          </div>
          <p>{t('groqKeyHelp')}</p>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '10px' }}>
            <button
              className="button secondary"
              onClick={testVoicePlayback}
              disabled={!speechAvailable()}
            >
              {testingVoice ? <VolumeX size={16} /> : <Volume2 size={16} />}
              {testingVoice ? t('stopSpeaking') : t('testGroqVoice')}
            </button>
            <a
              href="https://console.groq.com/keys"
              target="_blank"
              rel="noopener noreferrer"
              className="button secondary"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              <ExternalLink size={16} /> Groq Console
            </a>
          </div>
        </Panel>

        {/* Data Providers */}
        <Panel>
          <SectionHead title={t('dataProviderStatus')} />
          <div className="p3-settings-symbol">
            <ShieldCheck size={22} />
          </div>
          <p>{t('dataProviderNote')}</p>
          <Link to="/admin" className="button secondary">
            {t('viewProviderHealth')}
          </Link>
        </Panel>
      </div>
    </div>
  )
}
