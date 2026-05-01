import { useCallback, useRef, useState } from 'react'
import { api } from '../../lib/api'
import type { EnrollmentStatus, TrainingResult } from '../../lib/types'
import { useKeystrokeCapture } from '../../hooks/useKeystrokeCapture'
import { MetricCard } from '../ui/MetricCard'
import './enrollment.css'

const TYPING_PROMPTS = [
  'The quick brown fox jumps over the lazy dog. Pack my box with five dozen liquor jugs.',
  'How vexingly quick daft zebras jump! The five boxing wizards jump quickly.',
  'Sphinx of black quartz, judge my vow. Two driven jocks help fax my big quiz.',
  'Fix problem quickly with galvanized jets. Jackdaws love my big sphinx of quartz.',
  'Mr. Jock, TV quiz PhD, bags few lynx. Blowzy red vixens fight for a quick jump.',
]

interface EnrollmentPaneProps {
  onEnrolled: (userId: string) => void
}

type Phase = 'setup' | 'typing' | 'training' | 'complete'

export function EnrollmentPane({ onEnrolled }: EnrollmentPaneProps) {
  const [phase, setPhase] = useState<Phase>('setup')
  const [userId, setUserId] = useState('')
  const [status, setStatus] = useState<EnrollmentStatus | null>(null)
  const [result, setResult] = useState<TrainingResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [keystrokeCount, setKeystrokeCount] = useState(0)
  const [wpmDisplay, setWpmDisplay] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const promptIndex = useRef(0)
  const sessionId = useRef(`enroll-${Date.now()}`)

  const handleBurst = useCallback(async (state: {
    events: Array<{ key: string; press_time: number; release_time: number }>
    wpm: number
    errorCount: number
    wordCount: number
  }) => {
    if (!userId || state.events.length < 5) return
    setWpmDisplay(state.wpm)
    try {
      const resp = await api.submitBurst({
        user_id: userId,
        session_id: sessionId.current,
        events: state.events,
        wpm: state.wpm,
        error_count: state.errorCount,
        word_count: state.wordCount,
      })
      setKeystrokeCount(resp.keystroke_count)
      setStatus((prev) => prev ? { ...prev, keystroke_count: resp.keystroke_count, progress_pct: resp.progress_pct } : null)
    } catch (e) {
      // Non-fatal — burst just fails silently during typing
      void e
    }
  }, [userId])

  const { reset } = useKeystrokeCapture({
    onBurst: handleBurst,
    burstIntervalMs: 2500,
    minBurstSize: 6,
    enabled: phase === 'typing',
  })

  const handleStart = async () => {
    if (!userId.trim()) return
    setError(null)
    try {
      const s = await api.startEnrollment(userId.trim())
      setStatus(s)
      setKeystrokeCount(s.keystroke_count)
      if (s.is_trained) {
        onEnrolled(userId.trim())
        return
      }
      setPhase('typing')
      reset()
      textareaRef.current?.focus()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start enrollment')
    }
  }

  const handleTrain = async () => {
    setPhase('training')
    setError(null)
    try {
      const r = await api.trainModel(userId)
      setResult(r)
      setPhase('complete')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Training failed')
      setPhase('typing')
    }
  }

  const nextPrompt = () => {
    promptIndex.current = (promptIndex.current + 1) % TYPING_PROMPTS.length
    if (textareaRef.current) textareaRef.current.value = ''
    textareaRef.current?.focus()
  }

  const progress = status?.progress_pct ?? 0
  const readyToTrain = keystrokeCount >= 300

  return (
    <div className="enrollment">
      <header className="enrollment__header">
        <div className="enrollment__logo">
          <svg className="enrollment__logo-icon" viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <rect x="2" y="8" width="28" height="16" rx="3" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M8 16h4M14 13l3 3-3 3M19 16h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            <circle cx="16" cy="26" r="1.5" fill="currentColor"/>
          </svg>
          <span className="enrollment__logo-text">KEYSTROKE SENTINEL</span>
        </div>
        <h1 className="enrollment__title">
          Train your <span className="enrollment__title-accent">behavioral fingerprint</span>
        </h1>
        <p className="enrollment__subtitle">
          We analyze the invisible rhythm of your typing — dwell times, flight intervals, digraph
          latencies — and build a classifier that detects if someone else takes over your session.
        </p>
      </header>

      {phase === 'setup' && (
        <div className="enrollment__setup">
          <div>
            <label className="enrollment__field-label" htmlFor="user-id">User identity</label>
            <input
              id="user-id"
              className="enrollment__input"
              type="text"
              placeholder="alice@example.com"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') void handleStart() }}
              autoComplete="off"
            />
          </div>
          {error && <p style={{ color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)' }}>{error}</p>}
          <button className="enrollment__btn" onClick={void handleStart as unknown as React.MouseEventHandler} disabled={!userId.trim()}>
            Begin enrollment →
          </button>
        </div>
      )}

      {phase === 'typing' && (
        <div>
          <div className="enrollment__progress-section">
            <div className="enrollment__progress-bar-track">
              <div className="enrollment__progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="enrollment__progress-labels">
              <span>{keystrokeCount} / 300 keystrokes</span>
              <span>{Math.round(progress)}%</span>
            </div>
          </div>

          <div className="enrollment__typing-area">
            <div className="enrollment__prompt" aria-label="Typing prompt">
              {TYPING_PROMPTS[promptIndex.current]}
            </div>
            <textarea
              ref={textareaRef}
              className="enrollment__textarea"
              placeholder="Start typing here — your keystrokes are being captured…"
              aria-label="Type here to enroll your keystroke dynamics"
            />
            <p className="enrollment__hint">
              Type naturally. Corrections and pauses are part of your signature.
            </p>
          </div>

          <div className="enrollment__stats">
            <MetricCard label="Keystrokes" value={keystrokeCount} highlight="teal" />
            <MetricCard label="WPM" value={wpmDisplay} highlight="none" />
            <MetricCard label="Progress" value={`${Math.round(progress)}%`} highlight={readyToTrain ? 'teal' : 'none'} />
          </div>

          {error && <p style={{ color: 'var(--red)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', marginTop: '1rem' }}>{error}</p>}

          <div className="enrollment__actions">
            {readyToTrain ? (
              <button className="enrollment__btn" onClick={() => void handleTrain()}>
                Train classifier →
              </button>
            ) : (
              <button className="enrollment__btn" disabled>
                Keep typing ({300 - keystrokeCount} more to go)
              </button>
            )}
            <button className="enrollment__btn enrollment__btn--secondary" onClick={nextPrompt}>
              Next prompt
            </button>
          </div>
        </div>
      )}

      {phase === 'training' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
          <div className="spinner" aria-label="Training in progress" />
          Training Random Forest classifier…
        </div>
      )}

      {phase === 'complete' && result && (
        <div className="enrollment__complete">
          <p style={{ color: 'var(--teal)', fontFamily: 'var(--font-mono)' }}>
            ✓ Model trained. Cross-validated accuracy: <strong>{(result.accuracy * 100).toFixed(1)}%</strong>
          </p>

          <div>
            <p className="enrollment__field-label" style={{ marginBottom: 'var(--space-3)' }}>Cross-validation scores (5-fold)</p>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 'var(--space-2)', height: '60px' }}>
              {result.cv_scores.map((s, i) => (
                <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                  <div
                    className="enrollment__cv-bar"
                    style={{ height: `${s * 52}px`, width: '32px' }}
                    title={`Fold ${i + 1}: ${(s * 100).toFixed(1)}%`}
                  />
                  <span className="enrollment__cv-label">F{i + 1}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="enrollment__field-label" style={{ marginBottom: 'var(--space-3)' }}>Top feature importances</p>
            <div className="enrollment__feature-list">
              {Object.entries(result.feature_importance).slice(0, 8).map(([name, imp]) => (
                <div key={name} className="enrollment__feature-row">
                  <span className="enrollment__feature-name">{name}</span>
                  <div className="enrollment__feature-bar-track">
                    <div className="enrollment__feature-bar-fill" style={{ width: `${imp * 100 * 5}%` }} />
                  </div>
                  <span className="enrollment__feature-pct">{(imp * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          <button className="enrollment__btn" onClick={() => onEnrolled(userId)}>
            Start live monitoring →
          </button>
        </div>
      )}
    </div>
  )
}
