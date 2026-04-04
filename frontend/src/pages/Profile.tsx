import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchUserReports } from '../api/reports'
import { fetchOrders, fetchProfile, patchProfile } from '../api/user'
import BirthChartWheel from '../components/BirthChartWheel'
import { StarryBackground } from '../components/StarryBackground'
import { Icon } from '../components/icons/Icon'
import { CN_CITY_NAMES } from '../utils/cnCities'
import { placementsFromBirth } from '../utils/zodiacCalc'

export default function Profile() {
  const qc = useQueryClient()
  const profile = useQuery({ queryKey: ['profile'], queryFn: fetchProfile })
  const orders = useQuery({ queryKey: ['orders'], queryFn: fetchOrders })
  const reports = useQuery({ queryKey: ['userReports'], queryFn: fetchUserReports })

  const [nickname, setNickname] = useState('')
  const [birthDate, setBirthDate] = useState('')
  const [birthTime, setBirthTime] = useState('')
  const [birthPlaceName, setBirthPlaceName] = useState('')
  const [gender, setGender] = useState('')
  const [showForm, setShowForm] = useState(false)

  useEffect(() => {
    if (!profile.data) return
    setNickname(profile.data.nickname ?? '')
    setBirthDate(profile.data.birth_date ?? '')
    setBirthTime(profile.data.birth_time ?? '')
    setBirthPlaceName(profile.data.birth_place_name ?? '')
    setGender(profile.data.gender && profile.data.gender !== 'unknown' ? profile.data.gender : '')
  }, [profile.data])

  const save = useMutation({
    mutationFn: () =>
      patchProfile({
        nickname: nickname || undefined,
        birth_date: birthDate || undefined,
        birth_time: birthTime || undefined,
        gender: gender || undefined,
        birth_place_name: birthPlaceName || undefined,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['profile'] })
      setShowForm(false)
    },
  })

  const sun = profile.data?.sun_sign?.toLowerCase() ?? ''
  const reportCount = reports.data?.items?.length ?? 0
  const orderCount = orders.data?.items?.length ?? 0

  const chartPlacements = useMemo(() => {
    const bd = birthDate || profile.data?.birth_date
    if (!bd) return null
    const bt = birthTime || profile.data?.birth_time || null
    return placementsFromBirth(bd, bt)
  }, [birthDate, birthTime, profile.data?.birth_date, profile.data?.birth_time])

  return (
    <>
      <StarryBackground />
      <Link
        to="/"
        className="mb-4 inline-flex items-center gap-1 text-sm text-[var(--color-brand-gold)]"
      >
        ← 返回
      </Link>
      <h1 className="font-serif text-2xl font-medium tracking-tight text-[var(--color-text-primary)]">我的</h1>

      <section className="card-featured relative mt-8 overflow-hidden p-6 text-center">
        <img
          src="/illustrations/profile-avatar.png"
          alt=""
          className="pointer-events-none absolute -right-8 -top-10 h-40 w-40 object-contain opacity-50"
          aria-hidden
        />
        <div className="constellation-bg absolute inset-0 opacity-20" aria-hidden />
        <div className="relative mx-auto flex h-24 w-24 items-center justify-center overflow-hidden rounded-full border-2 border-[var(--color-brand-gold)]/40 bg-[var(--color-surface-3)]/50 shadow-[var(--shadow-glow-gold)]">
          {sun ? (
            <img
              src={`/zodiac/${sun.toLowerCase()}.png`}
              alt=""
              className="h-full w-full object-cover"
            />
          ) : (
            <Icon name="profile" size={40} className="text-[var(--color-brand-gold)]/80" />
          )}
        </div>
        <p className="relative mt-4 font-serif text-lg text-[var(--color-text-primary)]">
          {profile.data?.nickname?.trim() || '星友'}
        </p>
        {sun && (
          <p className="relative mt-1 text-xs capitalize text-[var(--color-text-secondary)]">
            太阳星座 · {sun}
          </p>
        )}
        <p className="relative mt-1 text-[10px] text-[var(--color-text-muted)]">ID {profile.data?.id ?? '—'}</p>

        <div className="relative mt-6 grid grid-cols-2 gap-3 text-center">
          <div className="rounded-xl border border-white/10 bg-black/25 py-3">
            <p className="font-mono text-xl text-[var(--color-brand-gold)]">{reportCount}</p>
            <p className="text-[10px] text-[var(--color-text-muted)]">已生成报告</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-black/25 py-3">
            <p className="font-mono text-xl text-[var(--color-brand-gold)]">{orderCount}</p>
            <p className="text-[10px] text-[var(--color-text-muted)]">订单记录</p>
          </div>
        </div>
      </section>

      {(profile.data?.referral_code || profile.data?.credit_yuan) && (
        <section className="card-elevated mt-5 space-y-3 p-4 text-sm">
          <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
            增长与奖励
          </p>
          {profile.data?.referral_code && (
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[var(--color-text-secondary)]">我的邀请码</span>
              <button
                type="button"
                className="font-mono text-xs text-[var(--color-brand-cyan)]"
                onClick={() => {
                  const u = `${window.location.origin}/?ref=${profile.data?.referral_code}`
                  void navigator.clipboard.writeText(u).then(
                    () => alert('已复制邀请链接'),
                    () => alert(profile.data?.referral_code ?? ''),
                  )
                }}
              >
                {profile.data.referral_code} · 复制链接
              </button>
            </div>
          )}
          {profile.data?.credit_yuan != null && (
            <p className="text-xs text-[var(--color-text-tertiary)]">
              账户抵扣金：¥{profile.data.credit_yuan}（好友首次付费后发放，合规单层奖励）
            </p>
          )}
          {profile.data?.season_pass_until && (
            <p className="text-xs text-emerald-200/90">
              星运月卡至 {new Date(profile.data.season_pass_until).toLocaleDateString('zh-CN')}
            </p>
          )}
          <div className="flex flex-col gap-2">
            <Link
              to="/season/today"
              className="inline-flex items-center gap-1 text-xs font-medium text-[var(--color-brand-gold)]"
            >
              今日深度运势（月卡）
              <Icon name="chevronRight" size={14} />
            </Link>
            {profile.data?.birth_date && (
              <Link
                to="/daily/personal"
                className="inline-flex items-center gap-1 text-xs font-medium text-emerald-200/90"
              >
                我的今日运势（本命 + 行运）
                <Icon name="chevronRight" size={14} />
              </Link>
            )}
          </div>
        </section>
      )}

      {chartPlacements && (
        <section className="card-elevated mt-5 p-5 text-center">
          <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
            我的示意星盘
          </p>
          <p className="mt-1 text-[11px] text-[var(--color-text-tertiary)]">
            示意展示；服务端报告已接入 Swiss Ephemeris 历表计算星盘参数
          </p>
          <div className="mt-4 flex justify-center">
            <BirthChartWheel
              sun={chartPlacements.sun}
              moon={chartPlacements.moon}
              rising={chartPlacements.rising}
              size={200}
            />
          </div>
        </section>
      )}

      <Link
        to="/quicktest"
        className="btn-glow relative mt-5 flex w-full items-center justify-center gap-2 rounded-2xl py-3.5 text-sm font-semibold"
      >
        <span className="relative z-[1] flex items-center gap-2 text-[#0a0b14]">
          免费星座解读
          <Icon name="chevronRight" size={16} />
        </span>
      </Link>

      <button
        type="button"
        onClick={() => setShowForm((v) => !v)}
        className="card-elevated mt-4 flex w-full items-center justify-between rounded-2xl border border-white/10 px-4 py-4 text-left text-sm text-[var(--color-text-primary)]"
      >
        <span>编辑资料</span>
        <span className={`text-[var(--color-text-muted)] transition-transform ${showForm ? 'inline-block rotate-90' : ''}`}>
          <Icon name="chevronRight" size={18} />
        </span>
      </button>

      {showForm && (
        <motion.section
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="card-elevated mt-3 space-y-3 overflow-hidden p-4 text-sm"
        >
          {profile.isLoading && <p className="text-[var(--color-text-muted)]">加载中…</p>}
          {profile.data && (
            <>
              <label className="block">
                <span className="text-[var(--color-text-secondary)]">昵称</span>
                <input
                  className="input-cosmic mt-1"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-[var(--color-text-secondary)]">出生日期</span>
                <input
                  type="date"
                  className="input-cosmic mt-1"
                  value={birthDate}
                  onChange={(e) => setBirthDate(e.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-[var(--color-text-secondary)]">出生时间</span>
                <input
                  type="time"
                  className="input-cosmic mt-1"
                  value={birthTime}
                  onChange={(e) => setBirthTime(e.target.value)}
                />
              </label>
              <label className="block">
                <span className="text-[var(--color-text-secondary)]">出生城市（可选，用于宫位与上升精度）</span>
                <select
                  className="input-cosmic mt-1"
                  value={birthPlaceName}
                  onChange={(e) => setBirthPlaceName(e.target.value)}
                >
                  <option value="">未选（默认北京经纬度）</option>
                  {CN_CITY_NAMES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="text-[var(--color-text-secondary)]">性别</span>
                <select
                  className="input-cosmic mt-1"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                >
                  <option value="">未选</option>
                  <option value="female">女</option>
                  <option value="male">男</option>
                </select>
              </label>
              <button
                type="button"
                onClick={() => save.mutate()}
                disabled={save.isPending}
                className="btn-glow relative w-full rounded-xl py-3 font-medium disabled:opacity-50"
              >
                <span className="relative z-[1] font-semibold text-[#0a0b14]">
                  {save.isPending ? '保存中…' : '保存资料'}
                </span>
              </button>
            </>
          )}
        </motion.section>
      )}

      <section className="card-elevated mt-6 p-4 text-sm">
        <h2 className="flex items-center gap-2 text-[var(--color-text-secondary)]">
          <Icon name="sparkle" size={16} />
          订单
        </h2>
        {orders.isLoading && <p className="mt-2 text-[var(--color-text-muted)]">加载中…</p>}
        <ul className="mt-3 space-y-2">
          {(orders.data?.items ?? []).map((o) => (
            <li key={o.order_id}>
              <Link
                to={`/payment/result?order_id=${encodeURIComponent(o.order_id)}`}
                className="flex items-center justify-between gap-2 rounded-xl border border-white/5 bg-black/20 p-3 text-xs transition-colors active:bg-black/35"
              >
                <span className="text-[var(--color-text-primary)]">{o.product_type}</span>
                <span className="flex items-center gap-1 font-medium text-[var(--color-brand-gold)]">
                  {o.status}
                  <Icon name="chevronRight" size={14} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <div className="mt-8 text-center">
        <Link
          to="/my-reports"
          className="inline-flex items-center gap-2 text-[var(--color-brand-gold)] underline-offset-4 hover:underline"
        >
          <Icon name="reports" size={18} />
          查看我的报告
        </Link>
      </div>
    </>
  )
}
