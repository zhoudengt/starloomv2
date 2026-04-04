import { motion } from 'framer-motion'
import { NavLink } from 'react-router-dom'
import { Icon, type IconName } from './icons/Icon'

const tabs: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: '/', label: '首页', icon: 'home', end: true },
  { to: '/fortunes', label: '运势', icon: 'fortune' },
  { to: '/my-reports', label: '报告', icon: 'reports' },
  { to: '/profile', label: '我的', icon: 'profile' },
]

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-white/[0.06] bg-[var(--color-surface-0)]/94 backdrop-blur-xl shadow-[0_-8px_32px_rgba(0,0,0,0.25)]">
      <div className="mx-auto flex h-16 max-w-md items-stretch safe-area-pb">
        {tabs.map(({ to, label, icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className="relative flex flex-1 flex-col items-center justify-center gap-0.5 pt-1 text-[10px] font-medium transition-colors"
          >
            {({ isActive }) => (
              <>
                <span
                  className={
                    isActive
                      ? 'text-[var(--color-brand-gold)]'
                      : 'text-[var(--color-text-tertiary)]'
                  }
                >
                  <Icon name={icon} size={22} />
                </span>
                <span
                  className={
                    isActive
                      ? 'text-[var(--color-brand-gold)]'
                      : 'text-[var(--color-text-muted)]'
                  }
                >
                  {label}
                </span>
                {isActive && (
                  <motion.span
                    layoutId="navDot"
                    className="absolute bottom-1 h-1 w-1 rounded-full bg-[var(--color-brand-gold)]"
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                  />
                )}
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
