import { scaleLinear, scaleTime } from '@visx/scale'
import {
  AnimatedLineSeries,
  Axis,
  Grid,
  XYChart
} from '@visx/xychart'
import { extent } from 'd3-array'
import { format } from 'date-fns'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import styled from 'styled-components'

interface DataPoint {
  x: string | Date
  y: number
  position?: number
  [key: string]: unknown
}

interface PnLLineSeriesConfig {
  dataKey: string
  data: DataPoint[]
  stroke: string
  name?: string
}

interface VisxPnLChartProps {
  height?: number
  margin?: { left: number; top: number; bottom: number; right: number }
  series: PnLLineSeriesConfig[]
  xAccessor?: (d: DataPoint) => Date
  yAccessor?: (d: DataPoint) => number
  formatTooltipX?: (value: Date) => string
  showGrid?: boolean
  numTicks?: number
}


const defaultAccessors = {
  xAccessor: (d: DataPoint) => new Date(d.x as string),
  yAccessor: (d: DataPoint) => d.y
}

interface TooltipState {
  x: number
  y: number
  datum: DataPoint
  lineConfig: PnLLineSeriesConfig
}

interface HoverState {
  xPosition: number
  tooltips: TooltipState[]
}

export function VisxPnLChart({
  height = 270,
  margin = { left: 60, top: 35, bottom: 38, right: 27 },
  series,
  xAccessor = defaultAccessors.xAccessor,
  yAccessor = defaultAccessors.yAccessor,
  formatTooltipX = (value: Date) => format(value, 'MMM d, yyyy'),
  showGrid = true,
  numTicks = 4
}: VisxPnLChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [hoverState, setHoverState] = useState<HoverState | null>(null)
  const [containerWidth, setContainerWidth] = useState(800)

  // Update container width when component mounts/resizes
  useEffect(() => {
    if (containerRef.current) {
      setContainerWidth(containerRef.current.clientWidth)
    }
  }, [])

  // Create scales for proper coordinate conversion
  const scales = useMemo(() => {
    const allData = series.flatMap(s => s.data)
    if (allData.length === 0) return null

    const xExtent = extent(allData, xAccessor) as [Date, Date]
    const yExtent = extent(allData, yAccessor) as [number, number]

    const xScale = scaleTime({
      domain: xExtent,
      range: [margin.left, containerWidth - margin.right]
    })

    const yScale = scaleLinear({
      domain: yExtent,
      range: [height - margin.bottom, margin.top]
    })

    return { xScale, yScale }
  }, [series, xAccessor, yAccessor, margin, height, containerWidth])

  const handlePointerMove = useCallback((params: { event?: React.PointerEvent<Element> | React.FocusEvent<Element, Element>; svgPoint?: { x: number; y: number } }) => {
    if (!params.event || !containerRef.current || !scales) return

    const containerRect = containerRef.current.getBoundingClientRect()
    const mouseX = (params.event as React.PointerEvent<Element>).clientX - containerRect.left

    // Convert mouse X to time domain
    const hoveredTime = scales.xScale.invert(mouseX)

    const newTooltips: TooltipState[] = []

    series.forEach((line) => {
      if (line.data.length === 0) return

      // Find closest data point by time
      let closestPoint = line.data[0]
      let minDistance = Infinity

      line.data.forEach((point) => {
        const distance = Math.abs(xAccessor(point).getTime() - hoveredTime.getTime())
        if (distance < minDistance) {
          minDistance = distance
          closestPoint = point
        }
      })

      // Use scales to get exact screen coordinates
      const xPos = scales.xScale(xAccessor(closestPoint))
      const yPos = scales.yScale(yAccessor(closestPoint))

      newTooltips.push({
        x: xPos,
        y: yPos,
        datum: closestPoint,
        lineConfig: line
      })
    })

    // Use the x position from the first tooltip for the vertical line
    const alignedXPosition = newTooltips.length > 0 ? newTooltips[0].x : mouseX

    setHoverState({
      xPosition: alignedXPosition,
      tooltips: newTooltips
    })
  }, [series, xAccessor, yAccessor, scales])

  return (
    <ChartWrapper
      ref={containerRef}
      onMouseLeave={() => setHoverState(null)}
    >
      <XYChart
        height={height}
        margin={margin}
        xScale={{ type: 'time' }}
        yScale={{ type: 'linear' }}
        onPointerMove={handlePointerMove}
      >
        <defs>
          <clipPath id="reveal-clip">
            <rect
              x={margin.left}
              y={margin.top}
              width="0"
              height={height - margin.top - margin.bottom}
              style={{
                animation: 'expandWidth 0.8s ease-out forwards'
              }}
            />
          </clipPath>
        </defs>
        {showGrid && (
          <Grid
            columns={false}
            rows={true}
            numTicks={numTicks}
            lineStyle={{
              stroke: 'hsl(var(--border))',
              strokeLinecap: 'round',
              strokeWidth: 1,
              strokeOpacity: 0.5
            }}
          />
        )}
        <Axis
          hideAxisLine
          hideTicks
          orientation="bottom"
          tickLabelProps={() => ({ dy: 10 })}
          left={30}
          numTicks={numTicks}
        />
        <Axis
          hideAxisLine
          hideTicks
          orientation="left"
          numTicks={numTicks}
          tickLabelProps={() => ({ dx: -10 })}
        />

        {series.map((line) => (
          <AnimatedLineSeries
            key={line.dataKey}
            stroke={line.stroke}
            dataKey={line.dataKey}
            data={line.data}
            xAccessor={xAccessor}
            yAccessor={yAccessor}
            style={{
              clipPath: 'url(#reveal-clip)'
            }}
          />
        ))}
      </XYChart>

      {/* Hover state: vertical line and tooltips */}
      {hoverState && (
        <>
          {/* Vertical hover line */}
          <div
            style={{
              position: 'absolute',
              left: hoverState.xPosition,
              top: margin.top,
              bottom: margin.bottom,
              width: '1px',
              backgroundColor: '#9ca3af',
              pointerEvents: 'none',
              zIndex: 999,
              height: height - margin.top - margin.bottom,
              transition: 'left 0.02s ease-out'
            }}
          />

          {/* Date label on top of vertical line */}
          <div
            style={{
              position: 'absolute',
              left: hoverState.xPosition,
              top: margin.top - 20,
              transform: 'translateX(-50%)',
              pointerEvents: 'none',
              zIndex: 1000,
              color: '#9ca3af',
              fontSize: '11px',
              fontWeight: '500',
              whiteSpace: 'nowrap',
              transition: 'left 0.02s ease-out'
            }}
          >
            {hoverState.tooltips.length > 0 && formatTooltipX(xAccessor(hoverState.tooltips[0].datum))}
          </div>

          {/* Tooltips and hover points */}
          {(() => {
            // Filter out duplicate y=0 tooltips
            const filteredTooltips = []
            let hasSeenZero = false
            
            hoverState.tooltips.forEach(tooltip => {
              const yValue = yAccessor(tooltip.datum)
              const isZero = Math.abs(yValue) < 0.001
              
              if (isZero) {
                if (!hasSeenZero) {
                  filteredTooltips.push(tooltip) // Keep first zero value
                  hasSeenZero = true
                }
                // Skip subsequent zero values
              } else {
                filteredTooltips.push(tooltip) // Keep all non-zero values
              }
            })
            
            // Sort from bottom to top (highest Y position first)
            const sortedTooltips = [...filteredTooltips].sort((a, b) => b.y - a.y)
            
            // Position tooltips bottom-up with overlap prevention
            const tooltipHeight = 24
            const gap = 2
            let lastBottom = height
            
            const repositionedTooltips = sortedTooltips.map(tooltip => {
              const originalTop = tooltip.y - tooltipHeight / 2
              let newTop = Math.min(originalTop, lastBottom - tooltipHeight - gap)
              newTop = Math.max(margin.top, newTop)
              
              lastBottom = newTop
              
              return {
                ...tooltip,
                adjustedY: newTop + tooltipHeight / 2
              }
            })
            
            return repositionedTooltips.map((tooltip, index) => (
              <div key={`tooltip-${tooltip.lineConfig.dataKey}-${index}`}>
                {/* Simple hover point - circle with white stroke */}
                <div
                  style={{
                    position: 'absolute',
                    left: tooltip.x - 5,
                    top: tooltip.y - 5,
                    width: '10px',
                    height: '10px',
                    borderRadius: '50%',
                    backgroundColor: tooltip.lineConfig.stroke,
                    border: '2px solid white',
                    pointerEvents: 'none',
                    zIndex: 1000,
                    transition: 'left 0.02s ease-out, top 0.02s ease-out'
                  }}
                />
                
                {/* Repositioned tooltip */}
                <div
                  style={{
                    position: 'absolute',
                    left: tooltip.x + 8,
                    top: tooltip.adjustedY,
                    transform: 'translateY(-50%)',
                    pointerEvents: 'none',
                    zIndex: 1001,
                    backgroundColor: tooltip.lineConfig.stroke,
                    color: 'white',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: '500',
                    whiteSpace: 'nowrap',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                    transition: 'left 0.02s ease-out, top 0.02s ease-out'
                  }}
                >
                  <strong>{yAccessor(tooltip.datum).toFixed(2)}</strong> - {(tooltip.lineConfig.name || tooltip.lineConfig.dataKey).substring(0, 20)}
                </div>
              </div>
            ))
          })()}
        </>
      )}
    </ChartWrapper>
  )
}

const ChartWrapper = styled.div`
  position: relative;
  max-width: 1000px;
  margin: 0 auto;
  
  text {
    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
  }

  .visx-axis-tick {
    text {
      font-size: 12px;
      font-weight: 400;
      fill: hsl(var(--muted-foreground));
    }
  }
  
  @keyframes expandWidth {
    from {
      width: 0;
    }
    to {
      width: 100%;
    }
  }
`

