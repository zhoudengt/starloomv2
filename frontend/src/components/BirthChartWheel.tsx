import { motion } from 'framer-motion'
import { useId } from 'react'
import { ZODIAC_CN, ZODIAC_ORDER, type ZodiacSlug } from '../utils/zodiacCalc'

const TWO_PI = Math.PI * 2
const SEG = TWO_PI / 12

function segmentCenterRad(index: number) {
  return -Math.PI / 2 + index * SEG + SEG / 2
}

export type PlanetAnnotation = {
  label: string
  hint: string
}

type Props = {
  sun: ZodiacSlug
  moon: ZodiacSlug
  rising: ZodiacSlug
  size?: number
  drawProgress?: number
  className?: string
  showLegend?: boolean
  /** Inline labels on chart: dashed line from dot to text outside the ring */
  annotations?: {
    sun?: PlanetAnnotation
    moon?: PlanetAnnotation
    rising?: PlanetAnnotation
  }
}

export default function BirthChartWheel({
  sun,
  moon,
  rising,
  size = 220,
  drawProgress = 1,
  className = '',
  showLegend = true,
  annotations,
}: Props) {
  const uid = useId().replace(/:/g, '')
  const gradId = `wheelGold-${uid}`

  const cx = size / 2
  const cy = size / 2
  const rOuter = size * 0.46
  const rInner = size * 0.34
  const rPlanetSun = size * 0.22
  const rPlanetMoon = rPlanetSun * 0.92
  const rPlanetRising = rPlanetSun * 0.88

  const sunI = ZODIAC_ORDER.indexOf(sun)
  const moonI = ZODIAC_ORDER.indexOf(moon)
  const risingI = ZODIAC_ORDER.indexOf(rising)

  const outerCirc = 2 * Math.PI * rOuter
  const dashOffset = outerCirc * (1 - Math.min(1, Math.max(0, drawProgress)))

  const pad = annotations ? size * 0.31 : 0
  const vb = annotations ? `${-pad} ${-pad} ${size + 2 * pad} ${size + 2 * pad}` : `0 0 ${size} ${size}`
  const svgW = annotations ? size + 2 * pad : size
  const svgH = annotations ? size + 2 * pad : size

  const labelR = rOuter + size * 0.165

  return (
    <div className={`relative ${className}`}>
      <svg width={svgW} height={svgH} viewBox={vb} className="overflow-visible">
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#d4a853" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#8b7355" stopOpacity="0.5" />
          </linearGradient>
        </defs>

        {ZODIAC_ORDER.map((slug, i) => {
          const start = -Math.PI / 2 + i * SEG
          const end = start + SEG
          const large = SEG > Math.PI ? 1 : 0
          const x1 = cx + rOuter * Math.cos(start)
          const y1 = cy + rOuter * Math.sin(start)
          const x2 = cx + rOuter * Math.cos(end)
          const y2 = cy + rOuter * Math.sin(end)
          const ix1 = cx + rInner * Math.cos(start)
          const iy1 = cy + rInner * Math.sin(start)
          const ix2 = cx + rInner * Math.cos(end)
          const iy2 = cy + rInner * Math.sin(end)
          const isSun = i === sunI
          return (
            <g key={slug}>
              <path
                d={`M ${x1} ${y1} A ${rOuter} ${rOuter} 0 ${large} 1 ${x2} ${y2} L ${ix2} ${iy2} A ${rInner} ${rInner} 0 ${large} 0 ${ix1} ${iy1} Z`}
                fill={isSun ? 'rgba(212,168,83,0.14)' : 'rgba(255,255,255,0.03)'}
                stroke="rgba(255,255,255,0.08)"
                strokeWidth={0.5}
              />
            </g>
          )
        })}

        <motion.circle
          cx={cx}
          cy={cy}
          r={rOuter}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth={1.25}
          strokeDasharray={outerCirc}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          opacity={0.85}
          transform={`rotate(-90 ${cx} ${cy})`}
        />
        <circle cx={cx} cy={cy} r={rInner} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={1} />

        {ZODIAC_ORDER.map((slug, i) => {
          const ang = segmentCenterRad(i)
          const tx = cx + (rInner + (rOuter - rInner) * 0.5) * Math.cos(ang)
          const ty = cy + (rInner + (rOuter - rInner) * 0.5) * Math.sin(ang)
          const cn = ZODIAC_CN[slug]
          return (
            <text
              key={`t-${slug}`}
              x={tx}
              y={ty}
              textAnchor="middle"
              dominantBaseline="central"
              className="fill-[var(--color-text-muted)]"
              style={{ fontSize: size * 0.055, fontWeight: 500 }}
            >
              {cn.slice(0, 1)}
            </text>
          )
        })}

        <PlanetDot
          cx={cx}
          cy={cy}
          r={rPlanetSun}
          angle={segmentCenterRad(sunI)}
          color="#d4a853"
          sizeScale={size / 220}
        />
        <PlanetDot
          cx={cx}
          cy={cy}
          r={rPlanetMoon}
          angle={segmentCenterRad(moonI)}
          color="#a8a0d4"
          sizeScale={size / 220}
        />
        <PlanetDot
          cx={cx}
          cy={cy}
          r={rPlanetRising}
          angle={segmentCenterRad(risingI)}
          color="#6ba3d4"
          sizeScale={size / 220}
        />

        {annotations && (
          <>
            <PlanetAnnotationLine
              cx={cx}
              cy={cy}
              rDot={rPlanetSun}
              rLabel={labelR}
              angle={segmentCenterRad(sunI)}
              color="#f0c75e"
              annotation={annotations.sun}
              size={size}
            />
            <PlanetAnnotationLine
              cx={cx}
              cy={cy}
              rDot={rPlanetMoon}
              rLabel={labelR}
              angle={segmentCenterRad(moonI)}
              color="#c4b5fd"
              annotation={annotations.moon}
              size={size}
            />
            <PlanetAnnotationLine
              cx={cx}
              cy={cy}
              rDot={rPlanetRising}
              rLabel={labelR}
              angle={segmentCenterRad(risingI)}
              color="#7dd3fc"
              annotation={annotations.rising}
              size={size}
            />
          </>
        )}
      </svg>
      {showLegend && (
        <div className="mt-3 flex flex-wrap justify-center gap-x-4 gap-y-1 text-[10px] text-[var(--color-text-tertiary)]">
          <span>
            <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[#d4a853]" /> 太阳 {ZODIAC_CN[sun]}
          </span>
          <span>
            <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[#a8a0d4]" /> 月亮 {ZODIAC_CN[moon]}
          </span>
          <span>
            <span className="mr-1 inline-block h-2 w-2 rounded-full bg-[#6ba3d4]" /> 上升 {ZODIAC_CN[rising]}
          </span>
        </div>
      )}
    </div>
  )
}

function PlanetDot({
  cx,
  cy,
  r,
  angle,
  color,
  sizeScale,
}: {
  cx: number
  cy: number
  r: number
  angle: number
  color: string
  sizeScale: number
}) {
  const px = cx + r * Math.cos(angle)
  const py = cy + r * Math.sin(angle)
  const dotR = 5 * sizeScale
  return (
    <g>
      <circle cx={px} cy={py} r={dotR + 2} fill={color} opacity={0.2} />
      <circle cx={px} cy={py} r={dotR} fill={color} stroke="rgba(255,255,255,0.35)" strokeWidth={0.75} />
    </g>
  )
}

function PlanetAnnotationLine({
  cx,
  cy,
  rDot,
  rLabel,
  angle,
  color,
  annotation,
  size,
}: {
  cx: number
  cy: number
  rDot: number
  rLabel: number
  angle: number
  color: string
  annotation?: PlanetAnnotation
  size: number
}) {
  if (!annotation) return null
  const dotR = 5 * (size / 220)
  const x1 = cx + (rDot + dotR + 2) * Math.cos(angle)
  const y1 = cy + (rDot + dotR + 2) * Math.sin(angle)
  const x2 = cx + (rLabel - 4) * Math.cos(angle)
  const y2 = cy + (rLabel - 4) * Math.sin(angle)
  const lx = cx + rLabel * Math.cos(angle)
  const ly = cy + rLabel * Math.sin(angle)
  /** 左侧：文字向右排；右侧：end 锚点让文字向左排，避免靠右被裁切 */
  const anchor = lx < cx ? 'start' : 'end'
  const fs = Math.max(9, size * 0.038)
  const fsHint = Math.max(7.5, size * 0.032)

  return (
    <g>
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={color}
        strokeWidth={0.85}
        strokeDasharray="4 3"
        opacity={0.75}
      />
      <text
        x={lx}
        y={ly - fsHint * 0.35}
        textAnchor={anchor}
        dominantBaseline="auto"
        fill={color}
        style={{ fontSize: fs, fontWeight: 700 }}
      >
        {annotation.label}
      </text>
      <text
        x={lx}
        y={ly + fs * 0.85}
        textAnchor={anchor}
        dominantBaseline="auto"
        fill="rgba(255,255,255,0.78)"
        style={{ fontSize: fsHint }}
      >
        {annotation.hint}
      </text>
    </g>
  )
}
