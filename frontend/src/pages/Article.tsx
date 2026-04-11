import { Link, Navigate, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useArticle } from '../api/content'
import { getArticleBySlug } from '../data/zodiacArticles'
import IRRenderer, { IRMetaBar } from '../components/IRRenderer'
import { Icon } from '../components/icons/Icon'
import { isContentIr } from '../types/contentIr'
import { StarryBackground } from '../components/StarryBackground'
import { appendUtm } from '../utils/utm'

export default function Article() {
  const { slug } = useParams()
  const { data: apiArticle, isLoading, isError } = useArticle(slug ?? '')

  const staticArticle = getArticleBySlug(slug)

  const title = apiArticle?.title ?? staticArticle?.title
  const coverImage = apiArticle?.cover_image ?? staticArticle?.coverImage
  const body = apiArticle?.body ?? staticArticle?.body

  if (!isLoading && !title) {
    return <Navigate to="/" replace />
  }

  if (isLoading && !staticArticle) {
    return (
      <>
        <StarryBackground />
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--color-brand-cyan)] border-t-transparent" />
        </div>
      </>
    )
  }

  if (isError && !staticArticle) {
    return <Navigate to="/" replace />
  }

  return (
    <>
      <StarryBackground />
      <div className="mb-4 flex items-center justify-between">
        <Link to="/" className="inline-flex text-sm text-[var(--color-brand-gold)]">
          ← 返回首页
        </Link>
        <button
          type="button"
          onClick={() => {
            const shareUrl = appendUtm(window.location.href, 'article_share')
            if (navigator.share) {
              navigator.share({
                title: title ?? 'StarLoom',
                text: body?.slice(0, 100) ?? '',
                url: shareUrl,
              }).catch(() => {})
            } else {
              navigator.clipboard?.writeText(shareUrl)
            }
          }}
          className="flex items-center gap-1.5 rounded-full bg-white/[0.08] px-3 py-1.5 text-xs text-white/70 transition-colors active:bg-white/[0.15]"
        >
          <Icon name="share" size={14} />
          分享
        </button>
      </div>

      <div className="relative z-[1] overflow-hidden rounded-2xl border border-white/[0.08]">
        <img
          src={coverImage}
          alt=""
          className="h-40 w-full object-cover sm:h-44"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#08091a] via-[#08091a]/70 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 p-4">
          <h1 className="font-serif text-xl font-semibold leading-snug text-white drop-shadow-[0_2px_12px_rgba(0,0,0,0.75)]">
            {title}
          </h1>
        </div>
      </div>

      <article className="relative z-[1] mt-6 rounded-2xl border border-white/[0.06] bg-[#111228]/50 p-5">
        {apiArticle?.body_ir && isContentIr(apiArticle.body_ir) ? (
          <>
            <IRMetaBar meta={apiArticle.body_ir.meta} />
            <IRRenderer
              blocks={apiArticle.body_ir.blocks}
              className="article-markdown text-sm leading-relaxed text-[var(--color-text-secondary)]"
            />
          </>
        ) : (
          <div
            className="article-markdown text-sm leading-relaxed text-[var(--color-text-secondary)] [&_h2]:mt-6 [&_h2]:font-serif [&_h2]:text-base [&_h2]:text-[var(--color-text-primary)] [&_h2]:first:mt-0 [&_li]:my-1 [&_p]:my-3 [&_p]:first:mt-0 [&_strong]:text-[var(--color-text-primary)] [&_table]:my-4 [&_table]:w-full [&_table]:border-collapse [&_table]:text-xs [&_td]:border [&_td]:border-white/10 [&_td]:p-2 [&_th]:border [&_th]:border-white/10 [&_th]:p-2 [&_th]:text-left [&_ul]:list-disc [&_ul]:pl-5"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{body ?? ''}</ReactMarkdown>
          </div>
        )}
      </article>
    </>
  )
}
