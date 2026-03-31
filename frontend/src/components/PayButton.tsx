import { Link } from 'react-router-dom'

type Props = {
  title: string
  subtitle: string
  price: string
  to: string
}

export function PayButton({ title, subtitle, price, to }: Props) {
  return (
    <Link
      to={to}
      className="block rounded-2xl border border-[#f0c75e]/35 bg-gradient-to-br from-[#2d1b69]/90 to-[#1a0f3d]/90 p-4 shadow-lg backdrop-blur"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="font-serif text-base text-violet-50">{title}</div>
          <div className="mt-1 text-xs text-violet-200/70">{subtitle}</div>
        </div>
        <div className="shrink-0 rounded-full bg-[var(--color-starloom-gold)] px-3 py-1.5 text-sm font-semibold text-[#2d1b69]">
          ¥{price}
        </div>
      </div>
    </Link>
  )
}
