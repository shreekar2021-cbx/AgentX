import { useEffect, useRef, useState } from 'react'
import { Check, Mic, MicOff, Sparkles, Volume2, VolumeX, X, Send, Bot, User, ArrowRight } from 'lucide-react'
import { api } from '../lib/api'
import { useTranslation } from '../lib/i18n'
import { useUI } from '../lib/store'
import { createVoiceSession, speakText, stopSpeaking, voiceAvailable, speechAvailable, type VoiceSession } from '../lib/voice'

interface Message {
  id: string
  sender: 'user' | 'assistant'
  text: string
  quickActions?: string[]
  provider?: string
}

export default function VoiceAssistant() {
  const { language, setLanguage } = useUI()
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [recording, setRecording] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [inputText, setInputText] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [statusText, setStatusText] = useState<string>('')
  const voiceSession = useRef<VoiceSession | null>(null)
  const activeUtterance = useRef<{ stop: () => void } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    return () => {
      voiceSession.current?.stop()
      stopSpeaking()
    }
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, busy])

  const suggestedQuestions = [
    { key: 'questionPaddyYellow', crop: 'Paddy' },
    { key: 'questionTomatoPest', crop: 'Tomato' },
    { key: 'questionWeather', crop: undefined },
    { key: 'questionFertilizer', crop: undefined },
  ]

  function startListening() {
    stopCurrentAudio()
    const langCode = language === 'te' ? 'te-IN' : language === 'hi' ? 'hi-IN' : 'en-IN'
    const session = createVoiceSession(langCode, {
      onText: text => {
        setTranscript(text)
        setInputText(text)
      },
      onError: err => {
        setRecording(false)
        setStatusText(err)
      },
      onEnd: () => {
        setRecording(false)
      },
    })

    if (!session) {
      setStatusText('Microphone unavailable in this browser.')
      return
    }

    voiceSession.current = session
    setTranscript('')
    setInputText('')
    setRecording(true)
    setStatusText(t('listening'))
    try {
      session.start()
    } catch {
      setRecording(false)
      setStatusText('Microphone permission needed.')
    }
  }

  function stopListening() {
    voiceSession.current?.stop()
    setRecording(false)
    if (transcript.trim()) {
      handleSend(transcript.trim())
    } else {
      setStatusText('')
    }
  }

  function toggleRecording() {
    if (recording) {
      stopListening()
    } else {
      startListening()
    }
  }

  function stopCurrentAudio() {
    stopSpeaking()
    activeUtterance.current = null
    setSpeaking(false)
  }

  function playSpokenReply(text: string) {
    if (!speechAvailable()) return
    stopCurrentAudio()
    setSpeaking(true)
    const playback = speakText(text, language, {
      onStart: () => setSpeaking(true),
      onEnd: () => setSpeaking(false),
      onError: () => setSpeaking(false),
    })
    activeUtterance.current = playback
  }

  async function handleSend(textToSend?: string, cropContext?: string) {
    const query = (textToSend || inputText).trim()
    if (!query || busy) return

    stopCurrentAudio()
    if (recording) {
      voiceSession.current?.stop()
      setRecording(false)
    }

    const userMsg: Message = {
      id: crypto.randomUUID(),
      sender: 'user',
      text: query,
    }
    setMessages(prev => [...prev, userMsg])
    setInputText('')
    setTranscript('')
    setBusy(true)
    setStatusText(t('voiceThinking'))

    try {
      const response = await api.voiceAssist({
        query,
        language,
        crop: cropContext,
      })

      const botMsg: Message = {
        id: crypto.randomUUID(),
        sender: 'assistant',
        text: response.reply,
        quickActions: response.quick_actions,
        provider: response.provider,
      }
      setMessages(prev => [...prev, botMsg])
      setStatusText('')

      // Automatically speak the response aloud in natural voice
      playSpokenReply(response.reply)
    } catch (err) {
      const fallbackReply =
        language === 'te'
          ? 'క్షమించండి, మీ ప్రశ్నకు సమాధానం ఇవ్వడంలో అంతరాయం ఏర్పడింది. దయచేసి మళ్లీ ప్రయత్నించండి.'
          : 'Sorry, could not process the voice query right now. Please try again.'
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: 'assistant',
          text: fallbackReply,
        },
      ])
      setStatusText('')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {/* Floating Action Button */}
      <button
        className={`voice-fab ${open ? 'active' : ''} ${recording ? 'is-recording' : ''}`}
        onClick={() => setOpen(!open)}
        title={t('voiceAssistantTitle')}
        aria-label={t('voiceAssistantTitle')}
      >
        <span className="fab-pulse" />
        {recording ? <Mic size={24} className="mic-live-icon" /> : <Sparkles size={22} />}
        <span className="fab-label">{language === 'te' ? 'రైతు మిత్ర' : t('voiceAssistant')}</span>
      </button>

      {/* Voice Assistant Modal / Drawer */}
      {open && (
        <div className="voice-modal-backdrop" onClick={() => setOpen(false)}>
          <div className="voice-modal" onClick={e => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="voice-modal-header">
              <div className="voice-brand">
                <div className="voice-avatar">
                  <Bot size={22} />
                </div>
                <div>
                  <strong>{language === 'te' ? 'రైతు మిత్ర' : t('voiceAssistantTitle')}</strong>
                  <span className="voice-badge">
                    <Sparkles size={11} /> Groq AI · LLaMA 3.3
                  </span>
                </div>
              </div>
              <div className="voice-header-actions">
                <select
                  value={language}
                  onChange={e => setLanguage(e.target.value as 'en' | 'te' | 'hi')}
                  className="voice-lang-select"
                  aria-label={t('language')}
                >
                  <option value="te">తెలుగు</option>
                  <option value="en">English</option>
                  <option value="hi">हिन्दी</option>
                </select>
                <button
                  className="icon-button close-btn"
                  onClick={() => {
                    stopCurrentAudio()
                    setOpen(false)
                  }}
                  aria-label="Close"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Conversation Messages */}
            <div className="voice-messages">
              {messages.length === 0 ? (
                <div className="voice-intro">
                  <div className="voice-intro-icon">
                    <Sparkles size={32} />
                  </div>
                  <h3>{language === 'te' ? 'రైతు మిత్రకు స్వాగతం!' : t('voiceAssistantTitle')}</h3>
                  <p>{t('voiceAssistantDesc')}</p>

                  <div className="suggested-chips">
                    <small>{t('suggestedQuestions')}</small>
                    {suggestedQuestions.map(item => (
                      <button
                        key={item.key}
                        className="chip-btn"
                        onClick={() => handleSend(t(item.key as any), item.crop)}
                      >
                        <span>{t(item.key as any)}</span>
                        <ArrowRight size={14} />
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map(msg => (
                  <div key={msg.id} className={`voice-bubble-wrap ${msg.sender}`}>
                    <div className="bubble-icon">
                      {msg.sender === 'assistant' ? <Bot size={16} /> : <User size={16} />}
                    </div>
                    <div className="voice-bubble">
                      <p>{msg.text}</p>
                      {msg.quickActions && msg.quickActions.length > 0 && (
                        <div className="bubble-actions">
                          {msg.quickActions.map((action, i) => (
                            <span key={i} className="action-pill">
                              <Check size={12} /> {action}
                            </span>
                          ))}
                        </div>
                      )}
                      {msg.sender === 'assistant' && (
                        <div className="bubble-footer">
                          <button
                            className="listen-again-btn"
                            onClick={() => (speaking ? stopCurrentAudio() : playSpokenReply(msg.text))}
                          >
                            {speaking ? <VolumeX size={14} /> : <Volume2 size={14} />}
                            <span>{speaking ? t('stopSpeaking') : t('listenToDiagnosis')}</span>
                          </button>
                          {msg.provider && <span className="provider-tag">{msg.provider}</span>}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

              {busy && (
                <div className="voice-bubble-wrap assistant">
                  <div className="bubble-icon">
                    <Bot size={16} />
                  </div>
                  <div className="voice-bubble thinking">
                    <span className="dot-pulse" />
                    <span>{statusText || t('voiceThinking')}</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Speaking animation banner */}
            {speaking && (
              <div className="speaking-banner">
                <div className="sound-wave">
                  <span />
                  <span />
                  <span />
                  <span />
                </div>
                <span>{t('voiceSpeaking')}</span>
                <button onClick={stopCurrentAudio} className="stop-speech-btn">
                  <VolumeX size={15} />
                </button>
              </div>
            )}

            {/* Live Recording / Spoken Input Display */}
            {recording && (
              <div className="live-speech-box">
                <span className="listening-ping" />
                <p>{transcript || t('listening')}</p>
              </div>
            )}

            {/* Bottom Controls / Speech Bar */}
            <div className="voice-controls">
              <div className="voice-input-row">
                <button
                  className={`mic-trigger-btn ${recording ? 'recording' : ''}`}
                  onClick={toggleRecording}
                  title={recording ? t('stopRecording') : t('tapToSpeak')}
                  disabled={!voiceAvailable()}
                >
                  {recording ? <MicOff size={22} /> : <Mic size={22} />}
                </button>

                <input
                  type="text"
                  className="voice-text-input"
                  placeholder={recording ? t('listening') : t('typeYourQuestion')}
                  value={inputText}
                  onChange={e => setInputText(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter') handleSend()
                  }}
                  disabled={recording || busy}
                />

                <button
                  className="send-trigger-btn"
                  onClick={() => handleSend()}
                  disabled={!inputText.trim() || busy}
                  title={t('sendQuestion')}
                >
                  <Send size={18} />
                </button>
              </div>
              <div className="voice-footnote">
                <small>
                  {recording
                    ? `${t('listening')} (${language.toUpperCase()})`
                    : voiceAvailable()
                    ? t('askVoicePrompt')
                    : 'Voice input not supported in this browser. Type your query.'}
                </small>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
