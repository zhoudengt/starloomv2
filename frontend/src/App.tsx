import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

const Home = lazy(() => import('./pages/Home'))
const DailyFortune = lazy(() => import('./pages/DailyFortune'))
const ReportPersonality = lazy(() => import('./pages/ReportPersonality'))
const Compatibility = lazy(() => import('./pages/Compatibility'))
const AnnualReport = lazy(() => import('./pages/AnnualReport'))
const Payment = lazy(() => import('./pages/Payment'))
const PaymentResult = lazy(() => import('./pages/PaymentResult'))
const Profile = lazy(() => import('./pages/Profile'))
const Chat = lazy(() => import('./pages/Chat'))

function PageLoader() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center text-[var(--color-starloom-gold)]">
      加载中…
    </div>
  )
}

export default function App() {
  return (
    <div className="mx-auto min-h-screen max-w-md px-4 pb-10 pt-6">
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/daily/:sign" element={<DailyFortune />} />
          <Route path="/report/personality" element={<ReportPersonality />} />
          <Route path="/report/compatibility" element={<Compatibility />} />
          <Route path="/report/annual" element={<AnnualReport />} />
          <Route path="/payment" element={<Payment />} />
          <Route path="/payment/result" element={<PaymentResult />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
      <footer className="mt-10 text-center text-xs text-violet-200/70">
        本服务基于星座文化提供性格分析与运势参考，仅供娱乐，不构成任何决策建议。
      </footer>
    </div>
  )
}
