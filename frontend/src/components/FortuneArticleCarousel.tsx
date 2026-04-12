import { AnimatePresence, motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useArticles, type ArticleBrief } from '../api/content'
import { ZODIAC_ARTICLES } from '../data/zodiacArticles'
import { Icon } from './icons/Icon'

const INTERVAL_MS = 4000

const CATEGORY_COVER: Record<string, string> = {
  career: '/illustrations/personality-hero.png',
  wealth: '/illustrations/annual-hero.png',
  relationship: '/illustrations/compatibility-home.png',
  energy: '/illustrations/season-moon.png',
  general: '/illustrations/astro-event.png',
}

function CarouselCoverImage({
  src,
  category,
}: {
  src: string
  category: string
}) {
  const fallback = CATEGORY_COVER[category] ?? CATEGORY_COVER.general
  const [current, setCurrent] = useState(src)
  useEffect(() => {
    setCurrent(src)
  }, [src])
  return (
    <div className="absolute inset-0 bg-[#141024]">
      <img
        src={current}
        alt=""
        className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        loading="lazy"
        onError={() => setCurrent(fallback)}
      />
    </div>
  )
}

function useDocumentVisible(): boolean {
  const [visible, setVisible] = useState(
    () => typeof document !== 'undefined' && document.visibilityState === 'visible',
  )
  useEffect(() => {
    const onChange = () => setVisible(document.visibilityState === 'visible')
    document.addEventListener('visibilitychange', onChange)
    return () => document.removeEventListener('visibilitychange', onChange)
  }, [])
  return visible
}

type SlideItem = {
  slug: string
  title: string
  coverImage: string
  category: string
  fromApi: boolean
  readingMinutes?: number | null
}

function CarouselSkeleton() {
  return (
    <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-[#141024]/80">
      <div className="flex min-h-[210px] animate-pulse flex-col justify-end p-5">
        <div className="mb-2 h-3 w-24 rounded bg-white/10" />
        <div className="h-6 w-[85%] max-w-[90%] rounded bg-white/15" />
        <div className="mt-3 h-3 w-28 rounded bg-white/10" />
      </div>
    </div>
  )
}

export function FortuneArticleCarousel() {
  const { data, isPending, isError } = useArticles({ limit: 8, carousel: 1 })

  const items: SlideItem[] = useMemo(() => {
    if (isPending) return []
    if (data?.items?.length) {
      return data.items.map((a: ArticleBrief) => ({
        slug: a.slug,
        title: a.title,
        coverImage: a.cover_image,
        category: a.category,
        fromApi: true,
        readingMinutes: a.reading_minutes,
      }))
    }
    return ZODIAC_ARTICLES.map((a) => ({
      slug: a.slug,
      title: a.title,
      coverImage: a.coverImage,
      category: 'general',
      fromApi: false,
    }))
  }, [data, isPending])

  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const pageVisible = useDocumentVisible()
  const autoAdvance = pageVisible && !paused

  const safeLen = items.length
  const next = useCallback(() => {
    setIndex((i) => (safeLen ? (i + 1) % safeLen : 0))
  }, [safeLen])

  useEffect(() => {
    if (!autoAdvance || safeLen < 2) return
    const id = window.setInterval(next, INTERVAL_MS)
    return () => window.clearInterval(id)
  }, [autoAdvance, next, safeLen])

  useEffect(() => {
    setIndex(0)
  }, [safeLen])

  if (isPending) {
    return <CarouselSkeleton />
  }

  const current = items[index] ?? items[0]
  if (!current) return null

  const source = data?.carousel_source
  const ribbon = (() => {
    if (isError) return '接口异常 · 本地预览'
    if (data?.items?.length) {
      if (source === 'today') return '今日精选'
      if (source === 'yesterday') return '昨日精选 · 今日内容生成中'
      if (source === 'fallback') return '近期精选'
      if (source === 'empty') return '暂无今日更新 · 预览内容'
      return '精选'
    }
    if (source === 'empty') return '暂无今日更新 · 本地预览'
    return '本地预览 · 非实时数据'
  })()

  return (
    <div
      className="mt-4"
      role="region"
      aria-roledescription="carousel"
      aria-label="星座精选文章"
      onPointerEnter={() => setPaused(true)}
      onPointerLeave={() => setPaused(false)}
    >
      <div className="relative isolate overflow-hidden rounded-2xl border-2 border-[#a78bfa]/20 shadow-[0_0_32px_rgba(167,139,250,0.12)]">
        <AnimatePresence initial={false} mode="wait">
          <motion.div
            key={current.slug}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.28 }}
            aria-live="polite"
          >
            <Link
              to={`/articles/${current.slug}`}
              className="card-game-glow group relative z-0 block min-h-[210px] overflow-hidden rounded-2xl transition-transform active:scale-[0.99]"
            >
              <CarouselCoverImage src={current.coverImage} category={current.category} />
              <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b14] via-[#0a0b14]/65 to-transparent" />

              <div className="relative z-[1] flex min-h-[210px] flex-col justify-end p-5">
                <span className="absolute left-3 top-3 max-w-[78%] rounded-full bg-black/55 px-3 py-1 text-[10px] font-semibold leading-snug tracking-wide text-[#e9d5ff] ring-1 ring-white/15 backdrop-blur-sm">
                  {ribbon}
                </span>
                <span className="absolute right-3 top-3 rounded-full bg-[#a78bfa]/90 px-3 py-1.5 text-xs font-bold text-[#0a0b14] shadow-lg">
                  阅读
                </span>
                <p className="pr-16 text-lg font-bold leading-snug text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.65)]">
                  {current.title}
                </p>
                {current.fromApi && current.readingMinutes != null && current.readingMinutes > 0 ? (
                  <p className="mt-1 text-[10px] text-white/55">约 {current.readingMinutes} 分钟阅读</p>
                ) : null}
                <p className="mt-3 flex items-center gap-1 text-[11px] font-semibold text-[#c4b5fd] drop-shadow-[0_1px_4px_rgba(0,0,0,0.45)]">
                  查看全文
                  <Icon name="chevronRight" size={12} className="inline" />
                </p>
              </div>
            </Link>
          </motion.div>
        </AnimatePresence>

        {safeLen > 1 ? (
          <div
            className="pointer-events-none absolute bottom-3 left-0 right-0 z-20 flex justify-center gap-2"
            role="tablist"
            aria-label="文章切换"
          >
            {items.map((a, i) => (
              <button
                key={a.slug}
                type="button"
                role="tab"
                aria-selected={i === index}
                aria-label={`第 ${i + 1} 篇：${a.title}`}
                className={`pointer-events-auto h-2 rounded-full transition-all ${
                  i === index ? 'w-6 bg-[#c4b5fd]' : 'w-2 bg-white/35 hover:bg-white/55'
                }`}
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setIndex(i)
                }}
              />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  )
}
