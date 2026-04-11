import { useQuery } from '@tanstack/react-query'
import { api } from './client'

export type GuidePreviewItem = {
  category: string
  label: string
  icon: string
  title: string
  preview: string
  transit_basis: string | null
}

export type GuidePreviewResponse = {
  date: string
  sign: string
  has_access: boolean
  items: GuidePreviewItem[]
}

export type GuideFullResponse = {
  category: string
  label: string
  sign: string
  date: string
  title: string
  content: string
  preview: string
  transit_basis: string | null
  has_access: boolean
  content_ir?: Record<string, unknown> | null
}

export type GuideAccessResponse = {
  has_access: boolean
  date: string
}

export async function fetchGuidePreview(sign: string): Promise<GuidePreviewResponse> {
  const { data } = await api.get('/guide/preview', { params: { sign } })
  return data
}

export async function fetchGuideFull(category: string, sign: string): Promise<GuideFullResponse> {
  const { data } = await api.get(`/guide/${category}`, { params: { sign } })
  return data
}

export async function fetchGuideAccess(): Promise<GuideAccessResponse> {
  const { data } = await api.get('/guide/access')
  return data
}

export function useGuidePreview(sign: string | undefined) {
  return useQuery({
    queryKey: ['guide', 'preview', sign],
    queryFn: () => fetchGuidePreview(sign!),
    enabled: !!sign,
    staleTime: 5 * 60 * 1000,
  })
}

export function useGuideFull(category: string, sign: string | undefined) {
  return useQuery({
    queryKey: ['guide', 'full', category, sign],
    queryFn: () => fetchGuideFull(category, sign!),
    enabled: !!sign && !!category,
    staleTime: 5 * 60 * 1000,
  })
}

export function useGuideAccess(enabled = true) {
  return useQuery({
    queryKey: ['guide', 'access'],
    queryFn: fetchGuideAccess,
    enabled,
    staleTime: 60 * 1000,
  })
}
