import { useCallback, useRef, useState } from 'react'
import type { AnomalyResult } from '../../lib/types'
import { useAnomalyStream } from '../../hooks/useAnomalyStream'
import { useKeystrokeCapture } from '../../hooks/useKeystrokeCapture'
import { AnomalyWaveform } from './AnomalyWaveform'
import { FeatureDistribution } from './FeatureDistribution'
import { ScoreRing } from './ScoreRing'
import { ThresholdControl } from './ThresholdControl'
import { StatusBadge } from '../ui/StatusBadge'
import { MetricCard } from '../ui/MetricCard'
import { ReauthChallenge } from '../challenge/ReauthChallenge'
import './dashboard.css'

interface LiveDashboardProps {
  userId: string
  onSignOut: () => void
}

const SESSION_ID = `session-${Date.now()}`
const DEFAULT_THRESHOLD = 0.65

export function LiveDashboard({ userId, onSignOut }: LiveDashboardProps) {
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD)
  const [scoreHistory, setScoreHistory] = useState<number[]>([])
  const [lastResult, setLastResult] = useState<AnomalyResult | null>(null)
  const [burstCount, setBurstCount] = useState(0)
  const [showChallenge, setShowChallenge] = useState(false)
  const [challengeScore, setChallengeScore] = useState(0)
  const [wsError, setWsError] = useState<string | null>(null)
  const [totalKeystrokes, setTotalKeystrokes] = useState(0)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleScore = useCallback((result: AnomalyResult) => {
    setLastResult(result)
    setScoreHistory((prev) => [...prev, result.anomaly_score])
    setBurstCount((n) => n + 1)

    if (result.anomaly_score > threshold && !showChallenge) {
      setChallengeScore(result.anomaly_score)
      setShowChallenge(true)
    }
  }, [threshold, showChallenge])

  const { state: wsState, sendBurst } = useAnomalyStream({
    userId,
    sessionId: SESSION_ID,
    onScore: handleScore,
    onError: setWsError,
    enabled: true,
  })

  const handleBurst = useCallback((state: {
    events: Array<{ key: string; press_time: number; release_time: number }>
    wpm: number
    errorCount: number
    wordCount: number
  }) => {
    setTotalKeystrokes((n) => n + state.events.length)
    sendBurst({
      user_id: userId,
      session_id: SESSION_ID,
      events: state.events,
      wpm: state.wpm,
      error_count: state.errorCount,
      word_count: state.wordCount,
    })
  }, [userId, sendBurst])

  useKeystrokeCapture({
    onBurst: handleBurst,
    burstIntervalMs: 2500,
    minBurstSize: 6,
    enabled: wsState === 'connected' && !showChallenge,
  })

  const currentScore = lastResult?.anomaly_score ?? 0
  const isAnomalous = currentScore > threshold
  const features = lastResult?.feature_snapshot ?? {}

  const badgeStatus = wsState === 'connected'
    ? (isAnomalous ? 'anomaly' : 'safe')
    : wsState === 'connecting' ? 'pending'
    : wsState === 'error' ? 'error'
    : 'disconnected'

  const badgeLabel = wsState === 'connected'
    ? (isAnomalous ? 'anomaly' : 'nominal')
    : wsState

  return (
    <div className="dashboard">
      {/* Top bar */}
      <header className="dashboard__topbar">
        <div className="dashboard__brand">
          <svg className="dashboard__brand-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="2" y="6" width="20" height="12" rx="2" stroke="currentColor" strokeWidth="1.5"/>
            <path d="M6 12h3M11 10l2 2-2 2M15 12h3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <span className="dashboard__brand-name">KEYSTROKE SENTINEL</span>
        </div>

        <div className="dashboard__topbar-meta">
          <span className="dashboard__user-label">
            user: <span className="dashboard__user-id">{userId}</span>
          </span>
          <StatusBadge status={badgeStatus} label={badgeLabel} pulse={wsState === 'connected'} />
          <button
            onClick={onSignOut}
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--text-xs)',
              color: 'var(--text-muted)',
              padding: '4px 10px',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              background: 'none',
              cursor: 'pointer',
              letterSpacing: '0.04em',
            }}
          >
            sign out
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="dashboard__body">
        {/* Left: waveform + typing area */}
        <main className="dashboard__main">
          {wsError && (
            <div style={{ padding: 'var(--space-3) var(--space-4)', background: 'var(--red-dim)', border: '1px solid rgba(224,85,85,0.3)', borderRadius: 'var(--radius)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', color: 'var(--red)' }}>
              {wsError}
            </div>
          )}

          <div className={`waveform-panel${isAnomalous ? ' panel--anomaly' : ''}`}>
            <div className="waveform-panel__header">
              <span className="section-title">Behavioral waveform</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                {burstCount} bursts captured
              </span>
            </div>
            <AnomalyWaveform
              history={scoreHistory}
              threshold={threshold}
              height={150}
            />
          </div>

          {/* Feature distribution */}
          <div className="panel">
            <div className="section-header">
              <span className="section-title">Live feature snapshot</span>
            </div>
            <FeatureDistribution features={features} height={170} />
          </div>

          {/* Typing pad */}
          <div className="panel">
            <div className="section-header">
              <span className="section-title">Type anything — your session is being monitored</span>
            </div>
            <textarea
              ref={textareaRef}
              className="typing-pad__textarea"
              placeholder="Start typing naturally. Every keystroke is analyzed in real time…"
              aria-label="Monitored typing area"
            />
            <p className="typing-pad__hint" style={{ marginTop: 'var(--space-2)' }}>
              Bursts are sent every 2.5s · min 6 keystrokes per burst
            </p>
          </div>
        </main>

        {/* Right sidebar */}
        <aside className="dashboard__sidebar">
          <div>
            <div className="section-header">
              <span className="section-title">Session score</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <ScoreRing score={currentScore} threshold={threshold} size={130} />
            </div>
          </div>

          <div className="metrics-grid">
            <MetricCard label="Bursts" value={burstCount} size="sm" />
            <MetricCard label="Keystrokes" value={totalKeystrokes} size="sm" />
            <MetricCard
              label="Score"
              value={(currentScore * 100).toFixed(1)}
              unit="%"
              size="sm"
              highlight={isAnomalous ? 'amber' : 'teal'}
            />
            <MetricCard
              label="WPM"
              value={Math.round(features['wpm'] ?? 0)}
              size="sm"
            />
          </div>

          <ThresholdControl value={threshold} onChange={setThreshold} />

          <div className="panel" style={{ marginTop: 'auto' }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', lineHeight: 1.6 }}>
              Random Forest classifier scores each typing burst against your enrolled baseline.
              Score &gt; threshold triggers re-auth.
            </p>
          </div>
        </aside>
      </div>

      {showChallenge && (
        <ReauthChallenge
          anomalyScore={challengeScore}
          userId={userId}
          onConfirm={(_password) => {
            // In a real system this would verify the password server-side.
            // Here we just dismiss and reset the anomaly flag.
            setShowChallenge(false)
          }}
          onDismiss={() => {
            setShowChallenge(false)
            onSignOut()
          }}
        />
      )}
    </div>
  )
}
