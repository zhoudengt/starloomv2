import { motion } from 'framer-motion'
import { type ReactNode, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  genderizeSectionImagePath,
  resolveSectionImage,
  stripLeadingSectionIndex,
  type ReportGender,
} from '../utils/reportSectionImages'

function splitSections(md: string): { title: string; body: string }[] {
  const lines = md.split('\n')
  const sections: { title: string; body: string }[] = []
  let curTitle = '概述'
  let buf: string[] = []
  for (const line of lines) {
    if (line.startsWith('## ')) {
      if (buf.length) sections.push({ title: curTitle, body: buf.join('\n').trim() })
      curTitle = line.replace(/^##\s+/, '').trim()
      buf = []
    } else {
      buf.push(line)
    }
  }
  if (buf.length || sections.length === 0) {
    sections.push({ title: curTitle, body: buf.join('\n').trim() || md })
  }
  return sections
}

export type SectionImageMap = Record<string, string>

export default function MarkdownReport({
  content,
  header,
  sectionImages,
  gender,
}: {
  content: string
  header?: ReactNode
  /** Keyword (substring) → image public path; longest keyword wins per section title */
  sectionImages?: SectionImageMap
  /** When set, gendered section-* assets are selected (male default if omitted). */
  gender?: ReportGender
}) {
  const sections = useMemo(() => splitSections(content), [content])
  const [open, setOpen] = useState<Record<number, boolean>>(() =>
    Object.fromEntries(sections.map((_, i) => [i, true])),
  )

  if (!content.trim()) return null

  return (
    <article className="space-y-3 text-[var(--color-text-primary)]/95">
      {header}
      {sections.map((sec, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 14 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-40px' }}
          transition={{ duration: 0.4, delay: Math.min(i * 0.05, 0.3), ease: [0.22, 1, 0.36, 1] }}
          className="card-elevated overflow-hidden rounded-2xl border border-white/10"
        >
          <button
            type="button"
            className="flex w-full items-center justify-between gap-2 px-4 py-3.5 text-left"
            onClick={() => setOpen((o) => ({ ...o, [i]: !o[i] }))}
          >
            <span className="flex items-center gap-3">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--color-brand-gold)]/20 text-xs font-semibold text-[var(--color-brand-gold)]">
                {i + 1}
              </span>
              <span className="font-serif text-sm text-[var(--color-brand-gold)]">
                {stripLeadingSectionIndex(sec.title)}
              </span>
            </span>
            <span className="text-[var(--color-text-muted)]">{open[i] ? '−' : '+'}</span>
          </button>
          {open[i] && (() => {
            const src = genderizeSectionImagePath(
              sectionImages != null ? resolveSectionImage(sec.title, sectionImages) : undefined,
              gender,
            )
            return (
              <div className="relative border-t border-white/[0.06]">
                {src ? (
                  <div className="relative h-28 w-full shrink-0 overflow-hidden">
                    <img
                      src={src}
                      alt=""
                      className="h-full w-full object-cover"
                      loading="lazy"
                      aria-hidden
                    />
                    <div
                      className="pointer-events-none absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-[#0a0b14] via-[#0a0b14]/65 to-transparent"
                      aria-hidden
                    />
                  </div>
                ) : null}
                <div className="markdown-report px-4 py-4 text-[15px] leading-[1.7] text-[var(--color-text-secondary)] [&_a]:text-[var(--color-brand-gold)] [&_h3]:mt-3 [&_h3]:text-[var(--color-text-primary)] [&_li]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:mb-3 [&_strong]:text-[var(--color-text-primary)] [&_ul]:list-disc [&_ul]:pl-5">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{sec.body || '（本节暂无内容）'}</ReactMarkdown>
                </div>
              </div>
            )
          })()}
        </motion.div>
      ))}
    </article>
  )
}
