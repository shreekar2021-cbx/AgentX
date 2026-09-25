import { describe, expect, it, vi } from 'vitest'
import { createVoiceSession, voiceAvailable } from './voice'

describe('voice fallback', () => {
  it('keeps text input available when browser speech recognition is missing', () => {
    const browser = {} as Window
    expect(voiceAvailable(browser)).toBe(false)
    expect(createVoiceSession('te-IN', { onText: vi.fn(), onError: vi.fn(), onEnd: vi.fn() }, browser)).toBeNull()
  })

  it('sets the chosen language and exposes editable transcription', () => {
    class Recognition {
      static last: Recognition | undefined
      lang = ''; interimResults = false; continuous = true
      onresult?: (event: unknown) => void; onerror?: (event: unknown) => void; onend?: () => void
      start = vi.fn(); stop = vi.fn()
      constructor() { Recognition.last = this }
    }
    const browser = { SpeechRecognition: Recognition } as unknown as Window
    const onText = vi.fn()
    const session = createVoiceSession('hi-IN', { onText, onError: vi.fn(), onEnd: vi.fn() }, browser)
    expect(session).not.toBeNull()
    expect(Recognition.last?.lang).toBe('hi-IN')
    session?.start()
    Recognition.last?.onresult?.({ resultIndex: 0, results: [{ 0: { transcript: 'पीले पत्ते' }, isFinal: true }] })
    expect(onText).toHaveBeenCalledWith('पीले पत्ते')
  })
})
