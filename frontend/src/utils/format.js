export function formatNumber(value, money = false) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const sign = money ? '$' : ''
  const abs = Math.abs(value)
  const neg = value < 0 ? '-' : ''
  if (abs >= 1_000_000_000) return `${neg}${sign}${(abs / 1_000_000_000).toFixed(2)}B`
  if (abs >= 1_000_000) return `${neg}${sign}${(abs / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000) return `${neg}${sign}${(abs / 1_000).toFixed(1)}K`
  if (money) return `${neg}$${abs.toFixed(2)}`
  if (Number.isInteger(value)) return value.toLocaleString()
  return value.toFixed(2)
}

export function stripExt(name) {
  return name.replace(/\.[^/.]+$/, '')
}
