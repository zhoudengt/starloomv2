/**
 * Content IR — intermediate representation for articles, guides, and reports.
 * Mirrors backend `app.content_ir_types` / `markdown_to_ir` output.
 */
export const CONTENT_IR_VERSION = '1' as const

export type CalloutStyle = 'tip' | 'warning' | 'insight' | 'action'

export type ContentIrMeta = {
  title?: string
  subtitle?: string
  reading_minutes?: number
  tags?: string[]
  cover_image?: string
  transit_basis?: string
}

export type BlockHeading = { type: 'heading'; level: 2 | 3; text: string }

export type BlockParagraph = { type: 'paragraph'; text: string }

export type BlockList = { type: 'list'; ordered: boolean; items: string[] }

export type BlockQuote = { type: 'quote'; text: string; source?: string }

export type BlockCallout = {
  type: 'callout'
  style: CalloutStyle
  title?: string
  text: string
}

export type BlockKeywordTag = { type: 'keyword_tag'; keywords: string[] }

export type BlockActionChecklist = {
  type: 'action_checklist'
  items: { scene: string; action: string; effect?: string }[]
}

export type BlockDivider = { type: 'divider' }

export type BlockImage = { type: 'image'; src: string; alt?: string; caption?: string }

export type ContentBlock =
  | BlockHeading
  | BlockParagraph
  | BlockList
  | BlockQuote
  | BlockCallout
  | BlockKeywordTag
  | BlockActionChecklist
  | BlockDivider
  | BlockImage

export type ContentIr = {
  version: typeof CONTENT_IR_VERSION
  meta: ContentIrMeta
  blocks: ContentBlock[]
}

export function isContentIr(x: unknown): x is ContentIr {
  if (!x || typeof x !== 'object') return false
  const o = x as Record<string, unknown>
  return o.version === '1' && Array.isArray(o.blocks) && o.meta !== undefined
}
