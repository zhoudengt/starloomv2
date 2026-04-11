import { useQuery } from '@tanstack/react-query'
import { fetchPrices } from '../api/payment'

const FALLBACK_PRICES: Record<string, number> = {
  personality: 0.1,
  compatibility: 0.2,
  annual: 0.3,
  chat: 0.1,
  personality_career: 0.07,
  personality_love: 0.07,
  personality_growth: 0.07,
  astro_event: 0.1,
  season_pass: 0.13,
  daily_guide: 0.04,
}

export function usePrices() {
  const query = useQuery({
    queryKey: ['prices'],
    queryFn: fetchPrices,
    staleTime: 300_000,
    select: (d) => d.prices,
  })
  return query
}

export function usePrice(product: string): string {
  const { data } = usePrices()
  if (data && data[product]) return Number(data[product]).toFixed(2)
  return (FALLBACK_PRICES[product] ?? 0.1).toFixed(2)
}
