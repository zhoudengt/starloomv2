import html2canvas from 'html2canvas'
import QRCode from 'qrcode'
import { useEffect, useRef, useState } from 'react'
import type { ReportStreamingKind } from './ReportGeneratingShell'

const SITE_URL = 'https://starloom.com.cn'

function stripMarkdownLite(s: string): string {
  return s
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .trim()
}

function excerpt(text: string, max = 400): string {
  const plain = stripMarkdownLite(text).replace(/\s+/g, ' ')
  if (plain.length <= max) return plain
  return `${plain.slice(0, max)}…`
}

export default function ReportExportActions({
  reportType,
  signCn,
  reportTitle,
  contentText,
}: {
  reportType: ReportStreamingKind
  signCn: string
  reportTitle: string
  contentText: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [busy, setBusy] = useState(false)
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null)
  const genTime = new Date().toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

  useEffect(() => {
    let cancelled = false
    void QRCode.toDataURL(SITE_URL, {
      width: 120,
      margin: 1,
      color: { dark: '#1a1530ff', light: '#f5f0ffff' },
    }).then((dataUrl) => {
      if (!cancelled) setQrDataUrl(dataUrl)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const capture = async () => {
    if (!ref.current) return null
    return html2canvas(ref.current, {
      scale: 2,
      backgroundColor: '#0a0b18',
      logging: false,
      useCORS: true,
    })
  }

  const save = async () => {
    if (!ref.current) return
    setBusy(true)
    try {
      const canvas = await capture()
      if (!canvas) return
      canvas.toBlob((blob) => {
        if (!blob) return
        const u = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = u
        a.download = `星盘研究所-${reportType}-${signCn}.png`
        a.click()
        URL.revokeObjectURL(u)
      })
    } finally {
      setBusy(false)
    }
  }

  const share = async () => {
    if (!ref.current) return
    setBusy(true)
    try {
      const canvas = await capture()
      if (!canvas) return
      const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, 'image/png'))
      if (blob && typeof navigator.share === 'function') {
        const file = new File([blob], `星盘研究所-${reportType}.png`, { type: 'image/png' })
        try {
          if (typeof navigator.canShare === 'function' && navigator.canShare({ files: [file] })) {
            await navigator.share({
              title: `${reportTitle} · 星盘研究所`,
              text: `${signCn} · ${reportTitle}`,
              files: [file],
            })
            return
          }
        } catch {
          /* fall through to save */
        }
      }
      await save()
    } catch {
      await save()
    } finally {
      setBusy(false)
    }
  }

  const body = excerpt(contentText)

  return (
    <div className="mt-8 space-y-4">
      <p className="text-center text-xs text-[var(--color-text-secondary)]">
        导出为图片（含水印与官网二维码），便于保存或分享
      </p>

      {/* Off-screen card for capture — inline styles for html2canvas */}
      <div className="pointer-events-none fixed left-[-9999px] top-0 z-0" aria-hidden>
        <div
          ref={ref}
          style={{
            width: 375,
            minHeight: 560,
            padding: 24,
            boxSizing: 'border-box',
            background: 'linear-gradient(165deg, #15182e 0%, #0a0b18 45%, #080914 100%)',
            borderRadius: 16,
            border: '1px solid rgba(255,255,255,0.08)',
            position: 'relative',
            overflow: 'hidden',
            fontFamily: 'system-ui, "PingFang SC", sans-serif',
            color: '#e8e6f4',
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: -40,
              opacity: 0.06,
              transform: 'rotate(-28deg)',
              fontSize: 52,
              fontWeight: 700,
              color: '#c9a227',
              pointerEvents: 'none',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.1,
            }}
          >
            星盘研究所 · 星盘研究所 · 星盘研究所
          </div>

          <p style={{ margin: 0, fontSize: 9, letterSpacing: '0.35em', textTransform: 'uppercase', color: '#8b87a8' }}>
            星盘研究所
          </p>
          <h2
            style={{
              margin: '12px 0 4px',
              fontSize: 20,
              fontWeight: 600,
              color: '#e8c96a',
              fontFamily: 'Georgia, "Songti SC", serif',
            }}
          >
            {reportTitle}
          </h2>
          <p style={{ margin: '0 0 16px', fontSize: 13, color: '#b8b4d0' }}>
            {signCn} · {genTime}
          </p>
          <div
            style={{
              position: 'relative',
              zIndex: 1,
              fontSize: 12,
              lineHeight: 1.75,
              color: '#c4c0dc',
              maxHeight: 280,
              overflow: 'hidden',
            }}
          >
            {body}
          </div>

          <div
            style={{
              marginTop: 20,
              display: 'flex',
              alignItems: 'flex-end',
              justifyContent: 'space-between',
              gap: 12,
              borderTop: '1px solid rgba(255,255,255,0.08)',
              paddingTop: 16,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ margin: 0, fontSize: 10, color: '#7a7694' }}>长按或扫码访问</p>
              <p style={{ margin: '6px 0 0', fontSize: 9, wordBreak: 'break-all', color: '#6b6788' }}>{SITE_URL}</p>
            </div>
            {qrDataUrl ? (
              <img src={qrDataUrl} alt="" width={88} height={88} style={{ borderRadius: 8, background: '#fff', padding: 4 }} />
            ) : null}
          </div>
          <p style={{ margin: '16px 0 0', fontSize: 9, textAlign: 'center', color: '#5c5878' }}>
            星盘研究所 · starloom.com.cn · 仅供娱乐参考
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void save()}
          className="btn-ghost flex-1 rounded-xl py-3 text-sm text-[var(--color-text-primary)]"
        >
          下载报告图
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => void share()}
          className="btn-glow relative flex-1 rounded-xl py-3 text-sm font-semibold disabled:opacity-50"
        >
          <span className="relative z-[1] text-[#0a0b14]">{busy ? '生成中…' : '分享图片'}</span>
        </button>
      </div>
    </div>
  )
}
