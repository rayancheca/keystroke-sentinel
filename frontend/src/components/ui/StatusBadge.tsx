import './ui.css'

type Status = 'safe' | 'anomaly' | 'neutral' | 'pending' | 'connected' | 'disconnected' | 'error'

interface StatusBadgeProps {
  status: Status
  label?: string
  pulse?: boolean
}

export function StatusBadge({ status, label, pulse = false }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-badge--${status}`} aria-label={`Status: ${label ?? status}`}>
      <span className={`status-badge__dot${pulse ? ' status-badge__dot--pulse' : ''}`} />
      {label ?? status}
    </span>
  )
}
