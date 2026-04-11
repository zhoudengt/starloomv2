import { useQuery } from '@tanstack/react-query'
import { api } from './client'

export type ArticleBrief = {
  id: number
  slug: string
  title: string
  cover_image: string
  category: string
  cta_product: string | null
  publish_date: string | null
  view_count: number
  subtitle?: string | null
  reading_minutes?: number | null
}

export type ArticleDetail = ArticleBrief & {
  body: string
  tags: string | null
  body_ir?: Record<string, unknown> | null
}

export type TipItem = {
  id: number
  category: string
  tip_text: string
  transit_basis: string | null
  cta_product: string
  tip_date: string
  category_label: string
  category_icon: string
}

export type ArticlesResponse = {
  items: ArticleBrief[]
  total: number
  /** GET /articles?carousel=1 时：today | fallback | empty */
  carousel_source?: string | null
}

export type TipsResponse = {
  date: string
  tips: TipItem[]
}

export async function fetchArticles(
  params: {
    category?: string
    limit?: number
    offset?: number
    /** 1 = 首页轮播：北京当日优先，否则回退窗口 */
    carousel?: 0 | 1
  } = {},
): Promise<ArticlesResponse> {
  const { data } = await api.get('/articles', { params })
  return data
}

export async function fetchArticleBySlug(slug: string): Promise<ArticleDetail> {
  const { data } = await api.get(`/articles/${slug}`)
  return data
}

export async function fetchTodayTips(): Promise<TipsResponse> {
  const { data } = await api.get('/tips/today')
  return data
}

export function useArticles(
  params: { category?: string; limit?: number; carousel?: 0 | 1 } = {},
) {
  return useQuery({
    queryKey: ['articles', params],
    queryFn: () => fetchArticles(params),
    staleTime: 5 * 60 * 1000,
  })
}

export function useArticle(slug: string) {
  return useQuery({
    queryKey: ['article', slug],
    queryFn: () => fetchArticleBySlug(slug),
    enabled: !!slug,
  })
}

export function useTodayTips() {
  return useQuery({
    queryKey: ['tips', 'today'],
    queryFn: fetchTodayTips,
    staleTime: 10 * 60 * 1000,
  })
}
