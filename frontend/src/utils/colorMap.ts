/** Map Chinese color names from API to CSS hex (lucky_color is not always a valid CSS color). */
const COLOR_NAME_MAP: Record<string, string> = {
  红色: '#ef4444',
  橙色: '#f97316',
  黄色: '#eab308',
  金色: '#f0c75e',
  绿色: '#22c55e',
  蓝色: '#3b82f6',
  靛蓝色: '#4f46e5',
  紫色: '#a855f7',
  粉色: '#ec4899',
  白色: '#f8fafc',
  黑色: '#1e293b',
  灰色: '#94a3b8',
  灰蓝色: '#64748b',
  玫红色: '#e11d48',
  青色: '#06b6d4',
  棕色: '#92400e',
  米色: '#fef3c7',
  银色: '#cbd5e1',
  珊瑚色: '#fb7185',
  薰衣草色: '#c4b5fd',
  翡翠色: '#34d399',
  酒红色: '#9f1239',
  橄榄绿: '#65a30d',
  天蓝色: '#38bdf8',
  深蓝色: '#1e40af',
  浅粉色: '#fbcfe8',
  浅绿色: '#86efac',
  浅黄色: '#fef08a',
  深紫色: '#6b21a8',
  薄荷绿: '#6ee7b7',
  香槟色: '#fde68a',
  古铜色: '#b45309',
}

/**
 * Resolve a lucky color string to a CSS color. Handles Chinese names and hex/rgb if ever returned.
 */
export function resolveColor(name: string): string {
  const t = name?.trim() ?? ''
  if (!t) return '#64748b'
  if (/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(t)) return t
  if (/^rgb/i.test(t)) return t
  return COLOR_NAME_MAP[t] ?? '#64748b'
}
