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

  const cleanText = text.replace(/[*#_~`>]/g, '').trim()
  if (!cleanText) return null

  try {
    const UtteranceClass = speech.SpeechSynthesisUtterance || SpeechSynthesisUtterance
    const utterance = new UtteranceClass(cleanText)
    const langCode = language === 'te' ? 'te-IN' : language === 'hi' ? 'hi-IN' : 'en-IN'
    utterance.lang = langCode
    utterance.rate = options?.rate ?? (language === 'te' ? 0.9 : 1.0)

    try {
      const voices = speech.speechSynthesis.getVoices()
      const matchedVoice = voices.find(v => v.lang === langCode || v.lang.startsWith(langCode.slice(0, 2)))
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
