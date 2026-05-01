import { useRef, useState } from 'react'
import './challenge.css'

interface ReauthChallengeProps {
  anomalyScore: number
  userId: string
  onConfirm: (password: string) => void
  onDismiss: () => void
}

export function ReauthChallenge({ anomalyScore, userId, onConfirm, onDismiss }: ReauthChallengeProps) {
  const [password, setPassword] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleConfirm = () => {
    if (!password.trim()) {
      inputRef.current?.focus()
      return
    }
    onConfirm(password)
  }

  return (
    <div className="challenge-overlay" role="alertdialog" aria-labelledby="challenge-title" aria-modal="true">
      <div className="challenge-card">
        <svg className="challenge-card__icon" viewBox="0 0 48 48" fill="none" aria-hidden="true">
          <path d="M24 6L8 14v12c0 9.9 6.9 19.1 16 22 9.1-2.9 16-12.1 16-22V14L24 6z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
          <path d="M24 22v6M24 17v2" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
        </svg>

        <div>
          <h2 id="challenge-title" className="challenge-card__title">
            Behavioral anomaly <span className="challenge-card__title-accent">detected</span>
          </h2>
        </div>

        <p className="challenge-card__body">
          The typing pattern in this session diverges significantly from{' '}
          <strong style={{ color: 'var(--text-primary)' }}>{userId}</strong>'s enrolled baseline.
          Verify your identity to continue.
        </p>

        <div className="challenge-card__score">
          <span className="challenge-card__score-label">Anomaly score</span>
          <span className="challenge-card__score-value">{(anomalyScore * 100).toFixed(1)}%</span>
        </div>

        <div>
          <label
            htmlFor="reauth-password"
            style={{ display: 'block', marginBottom: 'var(--space-2)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}
          >
            Password
          </label>
          <input
            id="reauth-password"
            ref={inputRef}
            type="password"
            className="challenge-card__input"
            placeholder="Enter your password to confirm identity"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleConfirm() }}
            autoFocus
          />
        </div>

        <div className="challenge-card__actions">
          <button className="challenge-card__btn challenge-card__btn--primary" onClick={handleConfirm}>
            Confirm identity
          </button>
          <button className="challenge-card__btn challenge-card__btn--secondary" onClick={onDismiss}>
            End session
          </button>
        </div>
      </div>
    </div>
  )
}
