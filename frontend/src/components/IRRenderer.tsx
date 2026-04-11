import type { ReactNode } from 'react'
import type {
  ContentBlock,
  ContentIr,
  ContentIrMeta,
} from '../types/contentIr'
import { Icon } from './icons/Icon'

function renderInlineMarkup(text: string): ReactNode {
  const parts: ReactNode[] = []
  let remaining = text
  let key = 0
  while (remaining.length > 0) {
    const bold = remaining.match(/\*\*(.+?)\*\*/)
    const italic = remaining.match(/(?<!\*)\*([^*]+)\*(?!\*)/)
    let m: RegExpMatchArray | null = null
    let kind: 'bold' | 'italic' | null = null
    if (bold && (!italic || bold.index! <= (italic.index ?? 999))) {
      m = bold
      kind = 'bold'
    } else if (italic) {
      m = italic
      kind = 'italic'
    }
    if (!m || m.index === undefined || !kind) {
      parts.push(<span key={key++}>{remaining}</span>)
      break
    }
    if (m.index > 0) {
      parts.push(<span key={key++}>{remaining.slice(0, m.index)}</span>)
    }
    const inner = m[1]
    parts.push(
      kind === 'bold' ? (
        <strong key={key++} className="text-[var(--color-text-primary)]">
          {inner}
        </strong>
      ) : (
        <em key={key++} className="text-[var(--color-text-secondary)]">
          {inner}
        </em>
      ),
    )
    remaining = remaining.slice(m.index + m[0].length)
  }
  return <>{parts}</>
}

function CalloutIcon({ style }: { style: string }) {
  if (style === 'warning') return <Icon name="sparkle" size={16} className="text-amber-300" />
  if (style === 'action') return <Icon name="sparkle" size={16} className="text-emerald-300" />
  if (style === 'insight') return <Icon name="sparkle" size={16} className="text-violet-300" />
  return <Icon name="sparkle" size={16} className="text-sky-300" />
}

export default function IRRenderer({
  blocks,
  className = '',
}: {
  blocks: ContentBlock[]
  className?: string
}) {
  return (
    <div className={`space-y-4 ${className}`}>
      {blocks.map((b, i) => (
        <IRBlock key={i} block={b} />
      ))}
    </div>
  )
}

function IRBlock({ block }: { block: ContentBlock }) {
  switch (block.type) {
    case 'heading':
      if (block.level === 2) {
        return (
          <h2 className="mt-6 font-serif text-base font-semibold text-[var(--color-text-primary)] first:mt-0">
            {block.text}
          </h2>
        )
      }
      return (
        <h3 className="mt-4 font-serif text-sm font-semibold text-[var(--color-brand-gold)]">
          {block.text}
        </h3>
      )
    case 'paragraph':
      return (
        <p className="text-sm leading-relaxed text-[var(--color-text-secondary)] [&_strong]:text-[var(--color-text-primary)]">
          {renderInlineMarkup(block.text)}
        </p>
      )
    case 'list':
      return block.ordered ? (
        <ol className="list-decimal space-y-1.5 pl-5 text-sm text-[var(--color-text-secondary)]">
          {block.items.map((it, j) => (
            <li key={j}>{renderInlineMarkup(it)}</li>
          ))}
        </ol>
      ) : (
        <ul className="list-disc space-y-1.5 pl-5 text-sm text-[var(--color-text-secondary)]">
          {block.items.map((it, j) => (
            <li key={j}>{renderInlineMarkup(it)}</li>
          ))}
        </ul>
      )
    case 'quote':
      return (
        <blockquote className="border-l-2 border-[var(--color-brand-gold)]/50 bg-white/[0.03] px-4 py-3 text-sm italic text-[var(--color-text-secondary)]">
          {renderInlineMarkup(block.text)}
        </blockquote>
      )
    case 'callout': {
      const ring =
        block.style === 'warning'
          ? 'border-amber-500/35 bg-amber-500/10'
          : block.style === 'action'
            ? 'border-emerald-500/30 bg-emerald-500/10'
            : block.style === 'insight'
              ? 'border-violet-500/30 bg-violet-500/10'
              : 'border-sky-500/30 bg-sky-500/10'
      return (
        <div className={`rounded-xl border px-4 py-3 ${ring}`}>
          <div className="flex gap-2">
            <CalloutIcon style={block.style} />
            <div className="min-w-0 flex-1">
              {block.title ? (
                <p className="text-xs font-semibold text-[var(--color-text-primary)]">{block.title}</p>
              ) : null}
              <p className="mt-1 text-sm leading-relaxed text-[var(--color-text-secondary)]">
                {renderInlineMarkup(block.text)}
              </p>
            </div>
          </div>
        </div>
      )
    }
    case 'keyword_tag':
      return (
        <div className="flex flex-wrap gap-2">
          {block.keywords.map((k, j) => (
            <span
              key={j}
              className="rounded-full border border-[var(--color-brand-gold)]/35 bg-[var(--color-brand-gold)]/10 px-3 py-1 text-xs font-medium text-[var(--color-brand-gold)]"
            >
              {k}
            </span>
          ))}
        </div>
      )
    case 'action_checklist':
      return (
        <div className="space-y-3 rounded-xl border border-white/[0.08] bg-[#0d0e1a] p-4">
          {block.items.map((it, j) => (
            <div key={j} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-3 text-sm">
              {it.scene ? (
                <p className="text-[11px] font-medium text-[var(--color-text-muted)]">
                  场景 · {renderInlineMarkup(it.scene)}
                </p>
              ) : null}
              <p className="mt-1 text-[var(--color-text-primary)]">
                {renderInlineMarkup(it.action)}
              </p>
              {it.effect ? (
                <p className="mt-2 text-xs text-emerald-200/80">效果 · {renderInlineMarkup(it.effect)}</p>
              ) : null}
            </div>
          ))}
        </div>
      )
    case 'divider':
      return <hr className="my-6 border-0 bg-gradient-to-r from-transparent via-white/15 to-transparent" style={{ height: 1 }} />
    case 'image':
      return (
        <figure className="overflow-hidden rounded-xl border border-white/10">
          <img src={block.src} alt={block.alt ?? ''} className="h-auto w-full object-cover" loading="lazy" />
          {block.caption ? (
            <figcaption className="px-3 py-2 text-center text-[11px] text-[var(--color-text-muted)]">
              {block.caption}
            </figcaption>
          ) : null}
        </figure>
      )
    default:
      return null
  }
}

/** Group IR blocks by level-2 headings for report-style accordions */
export function splitContentIrIntoSections(
  ir: ContentIr | null | undefined,
): { title: string; blocks: ContentBlock[] }[] {
  if (!ir?.blocks?.length) return []
  const hasH2 = ir.blocks.some((b) => b.type === 'heading' && b.level === 2)
  if (!hasH2) {
    return [{ title: '正文', blocks: [...ir.blocks] }]
  }

  const sections: { title: string; blocks: ContentBlock[] }[] = []
  let cur: { title: string; blocks: ContentBlock[] } | null = null

  const flush = () => {
    if (cur && cur.blocks.length > 0) {
      sections.push(cur)
    }
    cur = null
  }

  for (const b of ir.blocks) {
    if (b.type === 'heading' && b.level === 2) {
      flush()
      cur = { title: b.text, blocks: [] }
    } else {
      if (!cur) {
        cur = { title: '正文', blocks: [] }
      }
      cur.blocks.push(b)
    }
  }
  flush()

  return sections
}

export function IRMetaBar({ meta }: { meta: ContentIrMeta }) {
  const bits: string[] = []
  if (meta.reading_minutes != null) bits.push(`约 ${meta.reading_minutes} 分钟阅读`)
  if (meta.subtitle) bits.push(meta.subtitle)
  if (!bits.length) return null
  return (
    <p className="text-[11px] text-[var(--color-text-muted)]">{bits.join(' · ')}</p>
  )
}
