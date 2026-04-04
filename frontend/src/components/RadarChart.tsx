/** 五维雷达图（感情/事业/社交/创造力/直觉）0–100 */

import { useId } from 'react'

const LABELS = ['感情', '事业', '社交', '创造', '直觉'] as const
const KEYS = ['love', 'career', 'social', 'creativity', 'intuition'] as const

const DEFAULT_HINT_COLORS: Record<(typeof KEYS)[number], string> = {
  love: '#f472b6',
  career: '#fbbf24',
  social: '#34d399',
  creativity: '#a78bfa',
  intuition: '#38bdf8',
}

type Dims = Partial<Record<(typeof KEYS)[number], number>>

type Hints = Partial<Record<(typeof KEYS)[number], string>>

export default function RadarChart({
  dimensions,
  size = 200,
  hints,
  hintColors,
}: {
  dimensions: Dims
  size?: number
  /** 各维度一句说明，显示在标签下方 */
  hints?: Hints
  /** 各维度文字颜色 */
  hintColors?: Partial<Record<(typeof KEYS)[number], string>>
}) {
  const uid = useId().replace(/:/g, '')
  const fillGradId = `radarFill-${uid}`

  const cx = size / 2
  const cy = size / 2
  const r = size * 0.36
  const values = KEYS.map((k) => Math.min(100, Math.max(0, dimensions[k] ?? 70)))
  const hasHints = hints != null && KEYS.some((k) => hints[k])
  const n = 5
  const angle = (i: number) => (-Math.PI / 2 + (i * 2 * Math.PI) / n) as number

  const points = values.map((v, i) => {
    const rr = (r * v) / 100
    return `${cx + rr * Math.cos(angle(i))},${cy + rr * Math.sin(angle(i))}`
  })

  const grid = [0.25, 0.5, 0.75, 1].map((g) => {
    const pts = Array.from({ length: n }, (_, i) => {
      const rr = r * g
      return `${cx + rr * Math.cos(angle(i))},${cy + rr * Math.sin(angle(i))}`
    })
    return pts.join(' ')
  })

  const lr = r + (hasHints ? 58 : 24)
  const fsLabel = Math.max(10, size * 0.042)
  const fsScore = Math.max(11, size * 0.045)
  const fsHint = Math.max(7.5, size * 0.028)
  const gapLabelScore = Math.max(8, fsLabel * 0.45)
  const gapScoreHint = Math.max(10, fsScore * 0.35)

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="overflow-visible">
        <defs>
          <linearGradient id={fillGradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f0c75e" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#a855f7" stopOpacity="0.25" />
          </linearGradient>
        </defs>
        {grid.map((p, idx) => (
          <polygon
            key={idx}
            points={p}
            fill="none"
            stroke="rgba(255,255,255,0.12)"
            strokeWidth={1}
          />
        ))}
        {KEYS.map((_, i) => (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={cx + r * Math.cos(angle(i))}
            y2={cy + r * Math.sin(angle(i))}
            stroke="rgba(255,255,255,0.15)"
            strokeWidth={1}
          />
        ))}
        <polygon
          points={points.join(' ')}
          fill={`url(#${fillGradId})`}
          stroke="#f0c75e"
          strokeWidth={1.5}
        />
        {LABELS.map((label, i) => {
          const k = KEYS[i]!
          const score = values[i]!
          const hint = hints?.[k]
          const col = hintColors?.[k] ?? DEFAULT_HINT_COLORS[k]
          const x = cx + lr * Math.cos(angle(i))
          const y = cy + lr * Math.sin(angle(i))
          const yLabel = hint ? y - fsScore - gapLabelScore : y
          const yScore = y
          const yHint = y + fsScore + gapScoreHint
          return (
            <g key={label}>
              <text
                x={x}
                y={yLabel}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={col}
                style={{ fontSize: fsLabel, fontWeight: 700 }}
              >
                {label}
              </text>
              {hint != null && hint !== '' && (
                <>
                  <text
                    x={x}
                    y={yScore}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill={col}
                    style={{ fontSize: fsScore, fontWeight: 800 }}
                  >
                    {score}%
                  </text>
                  <text
                    x={x}
                    y={yHint}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="rgba(255,255,255,0.72)"
                    style={{ fontSize: fsHint }}
                  >
                    {hint}
                  </text>
                </>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
