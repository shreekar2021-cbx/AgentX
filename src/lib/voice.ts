export type SpeechLanguage = 'en-IN' | 'te-IN' | 'hi-IN'

export interface VoiceSession { start: () => void; stop: () => void }
type RecognitionResult = { isFinal: boolean; 0: { transcript: string } }
type RecognitionEvent = { resultIndex: number; results: ArrayLike<RecognitionResult> }
type BrowserRecognition = { lang: string; interimResults: boolean; continuous: boolean; onresult: ((event: RecognitionEvent) => void) | null; onerror: ((event: { error: string }) => void) | null; onend: (() => void) | null; start: () => void; stop: () => void }
type SpeechWindow = Window & { SpeechRecognition?: new () => BrowserRecognition; webkitSpeechRecognition?: new () => BrowserRecognition }

export function voiceAvailable(win: Window = window): boolean { const speech = win as SpeechWindow; return Boolean(speech.SpeechRecognition || speech.webkitSpeechRecognition) }

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
