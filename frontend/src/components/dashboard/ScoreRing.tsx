import './dashboard.css'

interface ScoreRingProps {
  score: number
  threshold: number
  size?: number
}

export function ScoreRing({ score, threshold, size = 120 }: ScoreRingProps) {
  const radius = (size - 20) / 2
  const circumference = 2 * Math.PI * radius
  const fillPct = Math.min(score, 1)
  const dashOffset = circumference * (1 - fillPct)

  const isAnomalous = score > threshold
  const color = isAnomalous ? '#f0a028' : '#2dc6b2'
  const cx = size / 2
  const cy = size / 2

  return (
    <div className="score-ring">
      <svg
        className="score-ring__svg"
        width={size}
        height={size}
        aria-label={`Anomaly score: ${(score * 100).toFixed(1)}%`}
        role="img"
      >
        <circle className="score-ring__track" cx={cx} cy={cy} r={radius} />
        <circle
          className="score-ring__fill"
          cx={cx}
          cy={cy}
          r={radius}
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
        />
        {/* SVG text rotated back since the whole SVG is rotated -90deg */}
        <g transform={`rotate(90, ${cx}, ${cy})`}>
          <text
            x={cx}
            y={cy - 6}
            className="score-ring__label"
            fill={color}
          >
            {(score * 100).toFixed(0)}%
          </text>
          <text
            x={cx}
            y={cy + 14}
            className="score-ring__sublabel"
          >
            anomaly score
          </text>
        </g>
      </svg>
    </div>
  )
}
