import { useCallback, useEffect, useRef, useState } from 'react'
import type { KeyEvent } from '../lib/types'

interface CaptureState {
  events: KeyEvent[]
  wpm: number
  errorCount: number
  wordCount: number
}

interface UseCaptureOptions {
  onBurst: (state: CaptureState) => void
  burstIntervalMs?: number
  minBurstSize?: number
  enabled?: boolean
}

export function useKeystrokeCapture({
  onBurst,
  burstIntervalMs = 3000,
  minBurstSize = 8,
  enabled = true,
}: UseCaptureOptions) {
  const pendingEvents = useRef<KeyEvent[]>([])
  const pressTimestamps = useRef<Map<string, number>>(new Map())
  const wordCount = useRef(0)
  const errorCount = useRef(0)
  const charCount = useRef(0)
  const sessionStart = useRef(Date.now())
  const [isCapturing, setIsCapturing] = useState(enabled)

  const flush = useCallback(() => {
    const events = pendingEvents.current.splice(0)
    if (events.length < minBurstSize) return

    const elapsed = (Date.now() - sessionStart.current) / 60_000
    const wpm = elapsed > 0 ? charCount.current / 5 / elapsed : 0

    onBurst({
      events,
      wpm: Math.round(wpm),
      errorCount: errorCount.current,
      wordCount: wordCount.current,
    })
  }, [onBurst, minBurstSize])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (!isCapturing) return
    pressTimestamps.current.set(e.key, performance.now())
  }, [isCapturing])

  const handleKeyUp = useCallback((e: KeyboardEvent) => {
    if (!isCapturing) return
    const pressTime = pressTimestamps.current.get(e.key)
    if (pressTime === undefined) return

    pressTimestamps.current.delete(e.key)
    const releaseTime = performance.now()

    pendingEvents.current.push({
      key: e.key,
      press_time: pressTime,
      release_time: releaseTime,
    })

    charCount.current += 1

    if (e.key === ' ' || e.key === 'Enter') {
      wordCount.current += 1
    }
    if (e.key === 'Backspace') {
      errorCount.current += 1
    }
  }, [isCapturing])

  useEffect(() => {
    setIsCapturing(enabled)
  }, [enabled])

  useEffect(() => {
    if (!isCapturing) return
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [isCapturing, handleKeyDown, handleKeyUp])

  useEffect(() => {
    if (!isCapturing) return
    const interval = setInterval(flush, burstIntervalMs)
    return () => clearInterval(interval)
  }, [isCapturing, flush, burstIntervalMs])

  const reset = useCallback(() => {
    pendingEvents.current = []
    pressTimestamps.current.clear()
    wordCount.current = 0
    errorCount.current = 0
    charCount.current = 0
    sessionStart.current = Date.now()
  }, [])

  return { isCapturing, setIsCapturing, reset }
}
