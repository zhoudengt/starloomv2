import { api } from './client'

export type ReportListItem = {
  report_id: string
  report_type: string
  sign: string
  created_at: string | null
  excerpt: string
  order_id: string | null
}

export async function fetchUserReports() {
  const { data } = await api.get('/user/reports')
  return data as { items: ReportListItem[] }
}

export type ReportDetail = {
  report_id: string
  report_type: string
  sign: string
  input_data: Record<string, unknown>
  content: string
  content_ir?: Record<string, unknown> | null
  created_at: string | null
  order_id: string | null
}

export async function fetchReport(reportId: string) {
  const { data } = await api.get(`/reports/${reportId}`)
  return data as ReportDetail
}
