import './ui.css'

interface MetricCardProps {
  label: string
  value: string | number
  unit?: string
  highlight?: 'amber' | 'teal' | 'red' | 'none'
  size?: 'sm' | 'md' | 'lg'
}

export function MetricCard({
  label,
  value,
  unit,
  highlight = 'none',
  size = 'md',
}: MetricCardProps) {
  return (
    <div className={`metric-card metric-card--${size} metric-card--${highlight}`}>
      <div className="metric-card__label">{label}</div>
      <div className="metric-card__value">
        <span className="metric-card__number">{value}</span>
        {unit && <span className="metric-card__unit">{unit}</span>}
      </div>
    </div>
  )
}
