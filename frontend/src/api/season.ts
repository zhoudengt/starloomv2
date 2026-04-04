import { api } from './client'

export async function fetchSeasonToday() {
  const { data } = await api.get('/season/today')
  return data as { markdown: string; date: string }
}
