import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { fetchCompatSharePreview } from '../api/growth'
import { StarryBackground } from '../components/StarryBackground'

export default function ShareCompatPreview() {
  const { token } = useParams<{ token: string }>()
  const q = useQuery({
    queryKey: ['compatShare', token],
    queryFn: () => fetchCompatSharePreview(token!),
    enabled: !!token,
  })

  return (
    <>
      <StarryBackground />
      <div className="relative mt-4 min-h-[320px] overflow-hidden rounded-2xl border border-[var(--color-brand-pink)]/25 shadow-[0_0_40px_rgba(236,72,153,0.12)]">
        <img
          src="/illustrations/compatibility-home.png"
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0b14] via-[#0a0b14]/70 to-[#0a0b14]/25" />
        <div className="relative z-[1] flex min-h-[320px] flex-col justify-end p-6 text-center">
          <p className="text-xs text-white/70">StarLoom · 双人合盘预览</p>
          {q.isLoading && <p className="mt-4 text-sm text-white/90">载入中…</p>}
          {q.isError && <p className="mt-4 text-sm text-red-300">链接无效或已过期</p>}
          {q.data && (
            <>
              <p className="mt-4 font-serif text-xl font-bold text-white drop-shadow-md">
                {q.data.person1_name} × {q.data.person2_name}
              </p>
              <p className="mt-6 font-mono text-5xl font-bold text-[var(--color-brand-pink)] blur-sm">
                {q.data.preview_score}
              </p>
              <p className="mt-2 text-xs text-white/75">{q.data.hint}</p>
              <p className="mt-4 text-sm text-white/90">{q.data.cta}</p>
              <Link
                to="/report/compatibility"
                className="mt-6 inline-block rounded-full bg-[var(--color-brand-gold)] px-6 py-3 text-sm font-medium text-[#0a0b14]"
              >
                我也测一测
              </Link>
            </>
          )}
        </div>
      </div>
      <Link to="/" className="mt-8 block text-center text-xs text-[var(--color-text-muted)]">
        进入首页
      </Link>
    </>
  )
}
