import { motion } from 'framer-motion'
import { type ReactNode, useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ContentBlock, ContentIr } from '../types/contentIr'
import {
  genderizeSectionImagePath,
  isPersonalityStrengthsSectionTitle,
  resolveAnnualSectionImage,
  resolveCompatibilitySectionImage,
  resolvePersonalitySectionImage,
  resolveSectionImage,
  stripLeadingSectionIndex,
  type ReportGender,
} from '../utils/reportSectionImages'
import IRRenderer, { splitContentIrIntoSections } from './IRRenderer'

/**
 * Split markdown on `## ` headings. Lines before the first `## ` are **preamble** and are
 * merged into the first section body (so UI never shows a fake "概述" block from pre-heading text).
 */
function splitSections(md: string): { title: string; body: string }[] {
  const lines = md.split('\n')
  const firstH2 = lines.findIndex((l) => l.startsWith('## '))
  if (firstH2 === -1) {
    const body = md.trim()
    if (!body) return []
    return [{ title: '正文', body }]
  }
  const preambleText = firstH2 > 0 ? lines.slice(0, firstH2).join('\n').trim() : ''
  const fromFirstH2 = lines.slice(firstH2)
  const sections: { title: string; body: string }[] = []
  let curTitle = ''
  let buf: string[] = []
  let isFirstSection = true

  const flush = () => {
    if (!curTitle) return
    let body = buf.join('\n').trim()
    if (isFirstSection && preambleText) {
      body = preambleText + (body ? `\n\n${body}` : '')
    }
    isFirstSection = false
    sections.push({ title: curTitle, body })
    curTitle = ''
    buf = []
  }

  for (const line of fromFirstH2) {
    if (line.startsWith('## ')) {
      if (curTitle) flush()
      curTitle = line.replace(/^##\s+/, '').trim()
    } else {
      buf.push(line)
    }
  }
  if (curTitle) flush()
  return sections
}

export type SectionImageMap = Record<string, string>

export default function MarkdownReport({
  content,
  contentIr,
  header,
  sectionImages,
  gender,
  /** 性格报告：七章标题精确匹配插图，避免子串误配与重复用图 */
  usePersonalityCanonicalImages = false,
  /** 配对报告：六章标题精确匹配双人插图 */
  useCompatibilityCanonicalImages = false,
  /** 年度运势：七章标题精确匹配插图 */
  useAnnualCanonicalImages = false,
}: {
  content: string
  /** 当存在时优先：按 IR 分节渲染（与 content 并存，流式完成后后端写入） */
  contentIr?: ContentIr | null
  header?: ReactNode
  /** Keyword (substring) → image public path; longest keyword wins per section title */
  sectionImages?: SectionImageMap
  /** When set, gendered section-* assets are selected (male default if omitted). */
  gender?: ReportGender
  usePersonalityCanonicalImages?: boolean
  useCompatibilityCanonicalImages?: boolean
  useAnnualCanonicalImages?: boolean
}) {
  const sections = useMemo((): (
    | { title: string; mode: 'ir'; blocks: ContentBlock[] }
    | { title: string; mode: 'md'; body: string }
  )[] => {
    if (contentIr?.blocks?.length) {
      return splitContentIrIntoSections(contentIr).map((s) => ({ ...s, mode: 'ir' as const }))
    }
    return splitSections(content).map((s) => ({
      title: s.title,
      body: s.body,
      mode: 'md' as const,
    }))
  }, [content, contentIr])
  const [open, setOpen] = useState<Record<number, boolean>>(() =>
    Object.fromEntries(sections.map((_, i) => [i, true])),
  )

  useEffect(() => {
    setOpen(Object.fromEntries(sections.map((_, i) => [i, true])))
  }, [sections.length])

  if (!content.trim() && !contentIr?.blocks?.length) return null

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
            const rawSrc = usePersonalityCanonicalImages
              ? resolvePersonalitySectionImage(sec.title)
              : useCompatibilityCanonicalImages
                ? resolveCompatibilitySectionImage(sec.title)
                : useAnnualCanonicalImages
                  ? resolveAnnualSectionImage(sec.title)
                  : sectionImages != null
                    ? resolveSectionImage(sec.title, sectionImages)
                    : undefined
            const src = genderizeSectionImagePath(rawSrc, gender)
            const strengths = isPersonalityStrengthsSectionTitle(sec.title)
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
                <div
                  className={`markdown-report px-4 py-4 text-[15px] leading-[1.7] text-[var(--color-text-secondary)] [&_a]:text-[var(--color-brand-gold)] [&_h3]:mt-3 [&_h3]:text-[var(--color-text-primary)] [&_li]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:mb-3 [&_strong]:text-[var(--color-text-primary)] [&_ul]:list-disc [&_ul]:pl-5${strengths ? ' markdown-report--strengths' : ''}`}
                >
                  {sec.mode === 'ir' ? (
                    <IRRenderer blocks={sec.blocks} />
                  ) : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {sec.body || '（本节暂无内容）'}
                    </ReactMarkdown>
                  )}
                </div>
              </div>
            )
          })()}
        </motion.div>
      ))}
    </article>
  )
}
