import { AnimatePresence, motion } from 'framer-motion'
import { lazy, Suspense, useEffect } from 'react'
import { Link, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { login } from './api/user'
import BottomNav from './components/BottomNav'
import LoadingAnalysis from './components/LoadingAnalysis'
import { ToastContainer } from './components/Toast'
import { useStarloomHydrated } from './hooks/useStarloomHydrated'
import { useUserStore } from './stores/userStore'
import { trackPageView } from './utils/analytics'

const Home = lazy(() => import('./pages/Home'))
const FortuneHub = lazy(() => import('./pages/FortuneHub'))
const QuickTest = lazy(() => import('./pages/QuickTest'))
const DailyFortune = lazy(() => import('./pages/DailyFortune'))
const ReportPersonality = lazy(() => import('./pages/ReportPersonality'))
const Compatibility = lazy(() => import('./pages/Compatibility'))
const AnnualReport = lazy(() => import('./pages/AnnualReport'))
const Payment = lazy(() => import('./pages/Payment'))
const PaymentResult = lazy(() => import('./pages/PaymentResult'))
const Profile = lazy(() => import('./pages/Profile'))
const Chat = lazy(() => import('./pages/Chat'))
const MyReports = lazy(() => import('./pages/MyReports'))
const ReportView = lazy(() => import('./pages/ReportView'))
const ReportAstroEvent = lazy(() => import('./pages/ReportAstroEvent'))
const SeasonToday = lazy(() => import('./pages/SeasonToday'))
const ShareCompatPreview = lazy(() => import('./pages/ShareCompatPreview'))
const Article = lazy(() => import('./pages/Article'))
const Guide = lazy(() => import('./pages/Guide'))

function Shell() {
  const location = useLocation()
  const hydrated = useStarloomHydrated()
  const token = useUserStore((s) => s.token)
  const setToken = useUserStore((s) => s.setToken)
  const ensureDevice = useUserStore((s) => s.ensureDevice)

  useEffect(() => {
    trackPageView(location.pathname)
  }, [location.pathname])

  useEffect(() => {
    if (!hydrated) return
    if (useUserStore.getState().token) return
    const run = async () => {
      const deviceId = ensureDevice()
      const params = new URLSearchParams(window.location.search)
      const refInUrl = params.get('ref')
      if (refInUrl) {
        try {
          sessionStorage.setItem('starloom_ref', refInUrl)
        } catch {
          /* ignore */
        }
      }
      let ref: string | null = null
      try {
        ref = sessionStorage.getItem('starloom_ref')
      } catch {
        /* ignore */
      }
      try {
        const res = await login(deviceId, ref)
        setToken(res.access_token)
      } catch {
        /* offline */
      }
    }
    void run()
  }, [hydrated, ensureDevice, setToken, token])

  return (
    <div className="relative min-h-screen">
      <div className="mx-auto min-h-screen max-w-md px-5 pb-36 pt-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] as const }}
            className="min-h-[40vh]"
          >
            <Suspense fallback={<LoadingAnalysis message="载入中…" />}>
              <Outlet />
            </Suspense>
          </motion.div>
        </AnimatePresence>
        <footer className="mt-12 space-y-3 text-center text-[11px] leading-relaxed text-[var(--color-text-muted)]">
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-1">
            <Link
              to="/quicktest"
              className="text-[var(--color-brand-violet)] transition-colors active:text-[var(--color-brand-gold)]"
            >
              免费解读
            </Link>
            <Link
              to="/report/compatibility"
              className="text-[var(--color-brand-violet)] transition-colors active:text-[var(--color-brand-gold)]"
            >
              配对合盘
            </Link>
            <a
              href="mailto:643795362@qq.com"
              className="text-[var(--color-brand-violet)] transition-colors active:text-[var(--color-brand-gold)]"
            >
              联系我们
            </a>
          </div>
          <p className="text-[10px] text-[var(--color-text-tertiary)]">
            提意见 · 共创 · 投稿 · 合作 · 643795362@qq.com
          </p>
          <p>本服务基于星座文化提供性格分析与运势参考，仅供娱乐，不构成任何决策建议。</p>
        </footer>
      </div>
      <BottomNav />
    </div>
  )
}

export default function App() {
  return (
    <>
    <ToastContainer />
    <Routes>
      <Route element={<Shell />}>
        <Route path="/" element={<Home />} />
        <Route path="/fortunes" element={<FortuneHub />} />
        <Route path="/quicktest" element={<QuickTest />} />
        <Route path="/daily/personal" element={<DailyFortune personalMode />} />
        <Route path="/daily/:sign" element={<DailyFortune />} />
        <Route path="/report/personality" element={<ReportPersonality />} />
        <Route path="/report/compatibility" element={<Compatibility />} />
        <Route path="/report/annual" element={<AnnualReport />} />
        <Route path="/payment" element={<Payment />} />
        <Route path="/payment/result" element={<PaymentResult />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/my-reports" element={<MyReports />} />
        <Route path="/reports/:reportId" element={<ReportView />} />
        <Route path="/report/astro-event" element={<ReportAstroEvent />} />
        <Route path="/season/today" element={<SeasonToday />} />
        <Route path="/share/compat/:token" element={<ShareCompatPreview />} />
        <Route path="/articles/:slug" element={<Article />} />
        <Route path="/guide/:category" element={<Guide />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </>
  )
}
