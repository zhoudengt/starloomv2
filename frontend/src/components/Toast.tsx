import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'

type ToastItem = { id: number; message: string }

let _nextId = 0
let _addToast: ((msg: string) => void) | null = null

export function toast(message: string) {
  _addToast?.(message)
}

export function ToastContainer() {
  const [items, setItems] = useState<ToastItem[]>([])

  useEffect(() => {
    _addToast = (message: string) => {
      const id = ++_nextId
      setItems((prev) => [...prev.slice(-4), { id, message }])
      setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 2500)
    }
    return () => {
      _addToast = null
    }
  }, [])

  return (
    <div className="pointer-events-none fixed inset-x-0 top-[env(safe-area-inset-top,0px)] z-[9999] flex flex-col items-center gap-2 px-4 pt-4">
      <AnimatePresence>
        {items.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="pointer-events-auto max-w-xs rounded-xl border border-white/15 bg-[#1a1b36]/95 px-4 py-2.5 text-center text-sm text-white/90 shadow-lg backdrop-blur-md"
          >
            {t.message}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
