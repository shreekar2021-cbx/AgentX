export type SpeechLanguage = 'en-IN' | 'te-IN' | 'hi-IN'

export interface VoiceSession { start: () => void; stop: () => void }
type RecognitionResult = { isFinal: boolean; 0: { transcript: string } }
type RecognitionEvent = { resultIndex: number; results: ArrayLike<RecognitionResult> }
type BrowserRecognition = { lang: string; interimResults: boolean; continuous: boolean; onresult: ((event: RecognitionEvent) => void) | null; onerror: ((event: { error: string }) => void) | null; onend: (() => void) | null; start: () => void; stop: () => void }
type SpeechWindow = Window & {
  SpeechRecognition?: new () => BrowserRecognition
  webkitSpeechRecognition?: new () => BrowserRecognition
  SpeechSynthesisUtterance?: typeof SpeechSynthesisUtterance
  speechSynthesis?: SpeechSynthesis
}

let cachedVoices: SpeechSynthesisVoice[] = []

export function initVoices(win: SpeechWindow = window as SpeechWindow): void {
  if (win && win.speechSynthesis && typeof win.speechSynthesis.getVoices === 'function') {
    try {
      const v = win.speechSynthesis.getVoices()
      if (v && v.length) cachedVoices = v
      win.speechSynthesis.onvoiceschanged = () => {
        try {
          cachedVoices = win.speechSynthesis?.getVoices() ?? []
        } catch {}
      }
    } catch {}
  }
}

if (typeof window !== 'undefined') {
  initVoices(window as SpeechWindow)
}

export function voiceAvailable(win: Window = window): boolean {
  const speech = win as SpeechWindow
  return Boolean(speech.SpeechRecognition || speech.webkitSpeechRecognition)
}

export function createVoiceSession(language: SpeechLanguage, callbacks: { onText: (text: string) => void; onError: (message: string) => void; onEnd: () => void }, win: Window = window): VoiceSession | null {
  const speech = win as SpeechWindow
  const Constructor = speech.SpeechRecognition || speech.webkitSpeechRecognition
  if (!Constructor) return null
  const recognition = new Constructor()
  recognition.lang = language
  recognition.interimResults = true
  recognition.continuous = false
  recognition.onresult = event => {
    const parts: string[] = []
    for (let i = 0; i < event.results.length; i++) parts.push(event.results[i][0].transcript)
    callbacks.onText(parts.join(' ').trim())
  }
  recognition.onerror = event => callbacks.onError(`Speech recognition stopped: ${event.error}. You can type instead.`)
  recognition.onend = callbacks.onEnd
  return { start: () => recognition.start(), stop: () => recognition.stop() }
}

export function speechAvailable(win: Window = window): boolean {
  const speech = win as SpeechWindow
  return Boolean(speech.speechSynthesis && (speech.SpeechSynthesisUtterance || typeof SpeechSynthesisUtterance !== 'undefined'))
}

export function stopSpeaking(win: Window = window): void {
  const speech = win as SpeechWindow
  if (speech.speechSynthesis) {
    try { speech.speechSynthesis.cancel() } catch {}
  }
}

export function findBestVoice(voices: SpeechSynthesisVoice[], language: 'en' | 'te' | 'hi'): SpeechSynthesisVoice | undefined {
  if (!voices || !voices.length) return undefined

  if (language === 'te') {
    // 1. First priority: native Telugu locale
    const teExact = voices.find(v => v.lang.toLowerCase() === 'te-in' || v.lang.toLowerCase() === 'te')
    if (teExact) return teExact

    // 2. Second priority: named Telugu or తెలుగు (Microsoft Mohan, Microsoft Shruti, Google తెలుగు)
    const teNamed = voices.find(v => {
      const name = v.name.toLowerCase()
      return name.includes('telugu') || name.includes('mohan') || name.includes('shruti') || v.name.includes('తెలుగు')
    })
    if (teNamed) return teNamed

    // 3. Third priority: Indian natural voice (shares South Asian phonetics)
    const inVoice = voices.find(v => v.lang === 'en-IN' || v.lang === 'hi-IN' || v.name.toLowerCase().includes('india'))
    if (inVoice) return inVoice
  } else if (language === 'hi') {
    const hiVoice = voices.find(v => v.lang.toLowerCase() === 'hi-in' || v.lang.toLowerCase() === 'hi' || v.name.toLowerCase().includes('hindi'))
    if (hiVoice) return hiVoice
  } else {
    const enVoice = voices.find(v => v.lang === 'en-IN' || v.lang === 'en-US' || v.lang === 'en-GB')
    if (enVoice) return enVoice
  }

  return undefined
}

export function sanitizeSpokenTelugu(raw: string): string {
  // Cleans punctuation, technical parentheses, bullets like "01" so Telugu TTS flows naturally
  return raw
    .replace(/\([^\)]*\)/g, ' ') // remove parentheses content like (Alternaria, Cercospora)
    .replace(/\b0\d\b/g, '') // remove "01", "02"
    .replace(/[*#_~`>]/g, '') // remove markdown
    .replace(/\s+/g, ' ')
    .trim()
}

export function speakText(
  text: string,
  language: 'en' | 'te' | 'hi' = 'en',
  options?: {
    onStart?: () => void
    onEnd?: () => void
    onError?: (err: unknown) => void
    rate?: number
  },
  win: Window = window
): { stop: () => void } | null {
  const speech = win as SpeechWindow
  if (!speech.speechSynthesis) return null

  try { speech.speechSynthesis.cancel() } catch {}

  const cleanText = language === 'te' ? sanitizeSpokenTelugu(text) : text.replace(/[*#_~`>]/g, '').trim()
  if (!cleanText) return null

  try {
    const UtteranceClass = speech.SpeechSynthesisUtterance || SpeechSynthesisUtterance
    const utterance = new UtteranceClass(cleanText)
    const langCode = language === 'te' ? 'te-IN' : language === 'hi' ? 'hi-IN' : 'en-IN'
    utterance.lang = langCode
    // 0.84 rate provides a calm, clear, natural spoken Telugu cadence
    utterance.rate = options?.rate ?? (language === 'te' ? 0.84 : 1.0)
    utterance.pitch = 1.0

    try {
      const liveVoices = speech.speechSynthesis.getVoices()
      const voicesPool = liveVoices && liveVoices.length ? liveVoices : cachedVoices
      const matchedVoice = findBestVoice(voicesPool, language)
      if (matchedVoice) {
        utterance.voice = matchedVoice
      }
    } catch {}

    if (options?.onStart) utterance.onstart = () => options.onStart!()
    if (options?.onEnd) utterance.onend = () => options.onEnd!()
    if (options?.onError) utterance.onerror = (event: unknown) => options.onError!(event)

    speech.speechSynthesis.speak(utterance)

    return {
      stop: () => {
        try { speech.speechSynthesis?.cancel() } catch {}
      }
    }
  } catch (err) {
    if (options?.onError) options.onError(err)
    return null
  }
}
