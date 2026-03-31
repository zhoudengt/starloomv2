import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { fetchDailyAll, fetchSigns } from '../api/constellation'
import { login } from '../api/user'
import { PayButton } from '../components/PayButton'
import { StarryBackground } from '../components/StarryBackground'
import { ZodiacCard } from '../components/ZodiacCard'
import { useUserStore } from '../stores/userStore'

export default function Home() {
  const setToken = useUserStore((s) => s.setToken)
  const ensureDevice = useUserStore((s) => s.ensureDevice)

  useEffect(() => {
    const run = async () => {
      const deviceId = ensureDevice()
      try {
        const res = await login(deviceId)
        setToken(res.access_token)
      } catch {
        /* offline */
      }
    }
    void run()
  }, [ensureDevice, setToken])

  const { data: signsData } = useQuery({ queryKey: ['signs'], queryFn: fetchSigns })
  const { data: dailyAll } = useQuery({ queryKey: ['dailyAll'], queryFn: fetchDailyAll })

  const scoreMap = new Map(dailyAll?.items.map((i) => [i.sign, i.overall_score]) ?? [])

  const today = new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <>
      <StarryBackground />
      <header className="mb-6 text-center">
        <h1 className="font-serif text-2xl font-semibold tracking-wide text-[var(--color-starloom-gold)]">
          StarLoom
        </h1>
        <p className="mt-1 text-sm text-violet-200/80">星座性格分析 · 运势参考</p>
        <p className="mt-3 text-xs text-violet-300/60">今日运势 · {today}</p>
      </header>

      <section className="grid grid-cols-3 gap-3">
        {(signsData?.signs ?? []).map((s) => (
          <ZodiacCard
            key={s.sign}
            sign={s.sign}
            signCn={s.sign_cn}
            symbol={s.symbol}
            score={scoreMap.get(s.sign)}
          />
        ))}
      </section>

      <section className="mt-10 space-y-3">
        <h2 className="mb-2 font-serif text-lg text-[var(--color-starloom-gold)]">深度分析</h2>
        <PayButton
          title="个人星座性格报告"
          subtitle="AI 深度解读你的星座特质"
          price="9.9"
          to="/report/personality"
        />
        <PayButton
          title="星座配对分析"
          subtitle="看看你们的契合度与相处建议"
          price="19.9"
          to="/report/compatibility"
        />
        <PayButton title="年度运势参考" subtitle="新一年的节奏与成长方向" price="29.9" to="/report/annual" />
      </section>

      <div className="mt-8 flex justify-center gap-6 text-sm">
        <Link to="/profile" className="text-[var(--color-starloom-gold)] underline-offset-4 hover:underline">
          我的
        </Link>
        <Link to="/chat" className="text-violet-200 underline-offset-4 hover:underline">
          AI 顾问
        </Link>
      </div>
    </>
  )
}
