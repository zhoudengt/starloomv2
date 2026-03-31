import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const DEVICE_KEY = 'starloom_device_id'

function getOrCreateDeviceId(): string {
  let id = localStorage.getItem(DEVICE_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(DEVICE_KEY, id)
  }
  return id
}

type State = {
  token: string | null
  deviceId: string
  setToken: (t: string | null) => void
  ensureDevice: () => string
}

export const useUserStore = create<State>()(
  persist(
    (set, get) => ({
      token: null,
      deviceId: '',
      setToken: (t) => set({ token: t }),
      ensureDevice: () => {
        const cur = get().deviceId
        if (cur) return cur
        const id = getOrCreateDeviceId()
        set({ deviceId: id })
        return id
      },
    }),
    { name: 'starloom-user', partialize: (s) => ({ token: s.token, deviceId: s.deviceId }) },
  ),
)
