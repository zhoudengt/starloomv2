import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type BirthProfileGender = 'female' | 'male' | ''

export type ProfileLike = {
  birth_date?: string | null
  birth_time?: string | null
  birth_place_name?: string | null
  birth_place_lat?: number | null
  birth_place_lon?: number | null
  birth_tz?: string | null
  gender?: string | null
}

type State = {
  birthDate: string
  birthTime: string
  birthPlaceName: string
  birthPlaceLat: number | null
  birthPlaceLon: number | null
  birthTz: string | null
  gender: BirthProfileGender
  setBirthDate: (v: string) => void
  setBirthTime: (v: string) => void
  setBirthPlaceName: (v: string) => void
  setGender: (v: BirthProfileGender) => void
  setBirthPlaceMeta: (lat: number | null, lon: number | null, tz: string | null) => void
  /** Server fields win when present (non-null / non-empty). */
  applyFromProfile: (p: ProfileLike) => void
  /** After payment auto-fill — same merge rules as profile. */
  applyFromExtras: (ex: Record<string, unknown>) => void
}

function normGender(g: string | null | undefined): BirthProfileGender {
  if (g === 'female' || g === 'male') return g
  return ''
}

export const useBirthProfileStore = create<State>()(
  persist(
    (set) => ({
      birthDate: '1995-06-15',
      birthTime: '12:00',
      birthPlaceName: '',
      birthPlaceLat: null,
      birthPlaceLon: null,
      birthTz: null,
      gender: '',

      setBirthDate: (birthDate) => set({ birthDate }),
      setBirthTime: (birthTime) => set({ birthTime }),
      setBirthPlaceName: (birthPlaceName) => set({ birthPlaceName }),
      setGender: (gender) => set({ gender }),
      setBirthPlaceMeta: (birthPlaceLat, birthPlaceLon, birthTz) =>
        set({ birthPlaceLat, birthPlaceLon, birthTz }),

      applyFromProfile: (p) =>
        set((s) => ({
          birthDate: p.birth_date?.trim() ? p.birth_date : s.birthDate,
          birthTime: p.birth_time?.trim() ? p.birth_time : s.birthTime,
          birthPlaceName:
            p.birth_place_name != null && String(p.birth_place_name).trim() !== ''
              ? String(p.birth_place_name).trim()
              : s.birthPlaceName,
          birthPlaceLat:
            p.birth_place_lat != null && p.birth_place_lat !== undefined
              ? p.birth_place_lat
              : s.birthPlaceLat,
          birthPlaceLon:
            p.birth_place_lon != null && p.birth_place_lon !== undefined
              ? p.birth_place_lon
              : s.birthPlaceLon,
          birthTz: p.birth_tz?.trim() ? p.birth_tz : s.birthTz,
          gender:
            p.gender && p.gender !== 'unknown' ? normGender(p.gender) : s.gender,
        })),

      applyFromExtras: (ex) => {
        const bd = ex.birth_date
        const bt = ex.birth_time
        const bn = ex.birth_place_name
        const lat = ex.birth_place_lat
        const lon = ex.birth_place_lon
        const tz = ex.birth_tz
        const g = ex.gender
        set((s) => ({
          birthDate: typeof bd === 'string' && bd.trim() ? bd : s.birthDate,
          birthTime: typeof bt === 'string' && bt.trim() ? bt : s.birthTime,
          birthPlaceName:
            typeof bn === 'string' && bn.trim() !== '' ? bn.trim() : s.birthPlaceName,
          birthPlaceLat: typeof lat === 'number' && Number.isFinite(lat) ? lat : s.birthPlaceLat,
          birthPlaceLon: typeof lon === 'number' && Number.isFinite(lon) ? lon : s.birthPlaceLon,
          birthTz: typeof tz === 'string' && tz.trim() ? tz : s.birthTz,
          gender: typeof g === 'string' && g !== 'unknown' ? normGender(g) : s.gender,
        }))
      },
    }),
    {
      name: 'starloom-birth-profile',
      partialize: (s) => ({
        birthDate: s.birthDate,
        birthTime: s.birthTime,
        birthPlaceName: s.birthPlaceName,
        birthPlaceLat: s.birthPlaceLat,
        birthPlaceLon: s.birthPlaceLon,
        birthTz: s.birthTz,
        gender: s.gender,
      }),
    },
  ),
)
