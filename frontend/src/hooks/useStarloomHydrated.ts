import { useEffect, useState } from 'react'
import { useUserStore } from '../stores/userStore'

/** Zustand persist 从 localStorage 恢复完成后再为 true，避免未恢复时误触发 login 覆盖 token */
export function useStarloomHydrated(): boolean {
  const [hydrated, setHydrated] = useState(() => useUserStore.persist.hasHydrated())

  useEffect(() => {
    if (useUserStore.persist.hasHydrated()) {
      setHydrated(true)
      return
    }
    const unsub = useUserStore.persist.onFinishHydration(() => {
      setHydrated(true)
    })
    return unsub
  }, [])

  return hydrated
}
