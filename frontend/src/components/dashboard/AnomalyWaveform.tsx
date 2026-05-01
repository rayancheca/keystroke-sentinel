import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

interface DataPoint {
  index: number
  score: number
  isAnomalous: boolean
}

interface AnomalyWaveformProps {
  history: number[]
  threshold: number
  width?: number
  height?: number
}

const MARGINS = { top: 16, right: 12, bottom: 28, left: 44 }

export function AnomalyWaveform({
  history,
  threshold,
  width = 800,
  height = 160,
}: AnomalyWaveformProps) {
  const svgRef = useRef<SVGSVGElement>(null)

  useEffect(() => {
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const innerW = width - MARGINS.left - MARGINS.right
    const innerH = height - MARGINS.top - MARGINS.bottom

    const g = svg
      .append('g')
      .attr('transform', `translate(${MARGINS.left},${MARGINS.top})`)

    const windowSize = 60
    const data: DataPoint[] = history.slice(-windowSize).map((score, i) => ({
      index: i,
      score,
      isAnomalous: score > threshold,
    }))

    if (data.length === 0) {
      g.append('text')
        .attr('x', innerW / 2)
        .attr('y', innerH / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#4a5a6b')
        .attr('font-family', 'IBM Plex Mono, monospace')
        .attr('font-size', '12px')
        .text('Waiting for typing bursts…')
      return
    }

    const xScale = d3.scaleLinear().domain([0, Math.max(windowSize - 1, data.length - 1)]).range([0, innerW])
    const yScale = d3.scaleLinear().domain([0, 1]).range([innerH, 0])

    // Background grid
    g.append('g')
      .attr('class', 'grid')
      .selectAll('line')
      .data([0, 0.25, 0.5, 0.75, 1.0])
      .enter()
      .append('line')
      .attr('x1', 0)
      .attr('x2', innerW)
      .attr('y1', (d) => yScale(d))
      .attr('y2', (d) => yScale(d))
      .attr('stroke', '#202830')
      .attr('stroke-width', 1)

    // Threshold zone (above threshold)
    g.append('rect')
      .attr('x', 0)
      .attr('y', yScale(1))
      .attr('width', innerW)
      .attr('height', yScale(threshold) - yScale(1))
      .attr('fill', 'rgba(240, 160, 40, 0.06)')

    // Threshold line
    g.append('line')
      .attr('x1', 0)
      .attr('x2', innerW)
      .attr('y1', yScale(threshold))
      .attr('y2', yScale(threshold))
      .attr('stroke', '#b07018')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4 4')

    g.append('text')
      .attr('x', innerW - 4)
      .attr('y', yScale(threshold) - 5)
      .attr('text-anchor', 'end')
      .attr('fill', '#b07018')
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('font-size', '10px')
      .text(`threshold ${threshold.toFixed(2)}`)

    // Safe area fill
    const safeArea = d3.area<DataPoint>()
      .x((d) => xScale(d.index))
      .y0(innerH)
      .y1((d) => yScale(Math.min(d.score, threshold)))
      .curve(d3.curveCatmullRom)

    g.append('path')
      .datum(data)
      .attr('fill', 'rgba(45, 198, 178, 0.08)')
      .attr('d', safeArea)

    // Anomaly fill
    const anomalyArea = d3.area<DataPoint>()
      .x((d) => xScale(d.index))
      .y0((d) => yScale(Math.min(d.score, threshold)))
      .y1((d) => yScale(d.score))
      .curve(d3.curveCatmullRom)

    g.append('path')
      .datum(data)
      .attr('fill', 'rgba(240, 160, 40, 0.18)')
      .attr('d', anomalyArea)

    // Main line — teal below threshold, amber above
    const line = d3.line<DataPoint>()
      .x((d) => xScale(d.index))
      .y((d) => yScale(d.score))
      .curve(d3.curveCatmullRom)

    g.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', '#2dc6b2')
      .attr('stroke-width', 1.5)
      .attr('d', line)

    // Anomalous segment overlay
    const anomalousData = data.filter((d) => d.isAnomalous)
    if (anomalousData.length > 0) {
      g.selectAll('.anomaly-dot')
        .data(anomalousData)
        .enter()
        .append('circle')
        .attr('cx', (d) => xScale(d.index))
        .attr('cy', (d) => yScale(d.score))
        .attr('r', 3)
        .attr('fill', '#f0a028')
        .attr('stroke', 'none')
    }

    // Latest score dot
    const last = data[data.length - 1]
    if (last) {
      g.append('circle')
        .attr('cx', xScale(last.index))
        .attr('cy', yScale(last.score))
        .attr('r', 5)
        .attr('fill', last.isAnomalous ? '#f0a028' : '#2dc6b2')
        .attr('stroke', '#111418')
        .attr('stroke-width', 2)
    }

    // Y axis
    g.append('g')
      .call(
        d3.axisLeft(yScale)
          .tickValues([0, 0.25, 0.5, 0.75, 1.0])
          .tickFormat(d3.format('.2f'))
          .tickSize(0)
      )
      .call((a) => a.select('.domain').remove())
      .selectAll('text')
      .attr('fill', '#4a5a6b')
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('font-size', '10px')
      .attr('dx', '-4px')

    // X axis label
    g.append('text')
      .attr('x', innerW / 2)
      .attr('y', innerH + 22)
      .attr('text-anchor', 'middle')
      .attr('fill', '#4a5a6b')
      .attr('font-family', 'IBM Plex Mono, monospace')
      .attr('font-size', '10px')
      .text('← burst history (last 60)')

  }, [history, threshold, width, height])

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      aria-label="Anomaly score waveform"
      role="img"
    />
  )
}
