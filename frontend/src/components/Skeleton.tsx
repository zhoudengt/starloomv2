export function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-hidden />
}

export function DailyFortuneSkeleton() {
  return (
    <div className="space-y-4 px-1">
      <div className="flex justify-between gap-4">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-12 flex-1 rounded-xl" />
      </div>
      <div className="mx-auto">
        <Skeleton className="h-52 w-52 rounded-full" />
      </div>
      <Skeleton className="h-32 w-full rounded-2xl" />
      {[1, 2, 3, 4].map((i) => (
        <Skeleton key={i} className="h-16 w-full rounded-xl" />
      ))}
    </div>
  )
}
