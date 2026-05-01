import './dashboard.css'

interface ThresholdControlProps {
  value: number
  onChange: (v: number) => void
}

export function ThresholdControl({ value, onChange }: ThresholdControlProps) {
  return (
    <div className="threshold-control">
      <div className="threshold-control__header">
        <span className="threshold-control__label">Anomaly threshold</span>
        <span className="threshold-control__value">{value.toFixed(2)}</span>
      </div>
      <input
        type="range"
        className="threshold-control__slider"
        min={0.3}
        max={0.9}
        step={0.01}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        aria-label={`Anomaly detection threshold: ${value.toFixed(2)}`}
      />
      <div className="threshold-control__hints">
        <span>sensitive</span>
        <span>lenient</span>
      </div>
    </div>
  )
}
