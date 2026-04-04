import { Icon } from './icons/Icon'

export default function ReportCertificateHeader({
  badge,
  title,
  lines,
  watermark = '星盘研究所 · StarLoom',
}: {
  badge: string
  title: string
  lines: string[]
  watermark?: string
}) {
  return (
    <div className="relative mb-6 overflow-hidden rounded-2xl border border-white/[0.1] bg-gradient-to-br from-[var(--color-surface-2)]/95 via-[#08091a]/90 to-[var(--color-surface-1)]/95 p-6 text-center backdrop-blur-md">
      <div className="constellation-bg absolute inset-0 rounded-2xl opacity-[0.1]" aria-hidden />
      <p className="relative text-[10px] uppercase tracking-[0.35em] text-[var(--color-text-tertiary)]">
        {badge}
      </p>
      <p className="relative mt-2 font-serif text-xl font-medium tracking-tight text-[var(--color-brand-gold)]">
        {title}
      </p>
      <div className="relative mt-4 space-y-1.5 text-[13px] leading-relaxed text-[var(--color-text-secondary)]">
        {lines.map((l) => (
          <p key={l}>{l}</p>
        ))}
      </div>
      <p className="relative mt-4 text-[9px] tracking-widest text-[var(--color-text-muted)]/60">
        {watermark}
      </p>
      <div className="pointer-events-none absolute -right-4 -top-4 opacity-[0.08]">
        <Icon name="sparkle" size={120} className="text-[var(--color-brand-gold)]" />
      </div>
    </div>
  )
}
