import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

interface FeatureDistributionProps {
  features: Record<string, number>
  width?: number
  height?: number
}

const DISPLAY_FEATURES = [
  'dwell_mean',
  'dwell_std',
  'flight_mean',
  'flight_std',
  'wpm',
  'error_rate',
]

const FEATURE_LABELS: Record<string, string> = {
  dwell_mean: 'Dwell μ',
  dwell_std: 'Dwell σ',
  flight_mean: 'Flight μ',
  flight_std: 'Flight σ',
  wpm: 'WPM',
  error_rate: 'Err rate',
}

export function FeatureDistribution({ features, width = 400, height = 180 }: FeatureDistributionProps) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const displayKeys = DISPLAY_FEATURES.filter((k) => k in features)
    if (displayKeys.length === 0) {
      svg.append('text')
        .attr('x', width / 2).attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#4a5a6b')
        .attr('font-family', 'IBM Plex Mono, monospace')
        .attr('font-size', '11px')
        .text('Awaiting burst…')
      return
    }

    const margins = { top: 12, right: 12, bottom: 32, left: 12 }
    const innerW = width - margins.left - margins.right
    const innerH = height - margins.top - margins.bottom

    const g = svg.append('g').attr('transform', `translate(${margins.left},${margins.top})`)

    const values = displayKeys.map((k) => features[k] ?? 0)
    const maxVal = Math.max(...values, 1)

    const xScale = d3.scaleBand()
      .domain(displayKeys)
      .range([0, innerW])
      .padding(0.3)

    const yScale = d3.scaleLinear()
      .domain([0, maxVal * 1.1])
      .range([innerH, 0])

    // Bars
    g.selectAll('.bar')
      .data(displayKeys)
      .enter()
      .append('rect')
      .attr('x', (d) => xScale(d) ?? 0)
      .attr('y', (d) => yScale(features[d] ?? 0))
      .attr('width', xScale.bandwidth())
      .attr('height', (d) => innerH - yScale(features[d] ?? 0))
      .attr('fill', '#2dc6b2')
      .attr('opacity', 0.7)
      .attr('rx', 2)

    // Value labels on top of bars
    g.selectAll('.val-label')
      .data(displayKeys)
      .enter()
      .append('text')
      .attr('x', (d) => (xScale(d) ?? 0) + xScale.bandwidth() / 2)
      .attr('y', (d) => yScale(features[d] ?? 0) - 3)
      .attr('text-anchor', 'middle')
      .attr('fill', '#c8d8e8')
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('font-size', '9px')
      .text((d) => {
        const v = features[d] ?? 0
        return v < 10 ? v.toFixed(2) : Math.round(v).toString()
      })

    // X axis labels
    g.selectAll('.x-label')
      .data(displayKeys)
      .enter()
      .append('text')
      .attr('x', (d) => (xScale(d) ?? 0) + xScale.bandwidth() / 2)
      .attr('y', innerH + 14)
      .attr('text-anchor', 'middle')
      .attr('fill', '#4a5a6b')
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('font-size', '9px')
      .text((d) => FEATURE_LABELS[d] ?? d)

  }, [features, width, height])

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      aria-label="Live feature distribution"
      role="img"
    />
  )
}
