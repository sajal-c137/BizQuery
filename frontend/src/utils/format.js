// compact human-friendly numbers — mirrors the backend's _fmt_num
export function formatNumber(value, money = false) {
  // graceful handling of nulls / NaN
  if (value === null || value === undefined || Number.isNaN(value)) return '—'

  const sign = money ? '$' : ''
  const abs = Math.abs(value)
  const neg = value < 0 ? '-' : ''

  // billions / millions / thousands
  if (abs >= 1_000_000_000) return `${neg}${sign}${(abs / 1_000_000_000).toFixed(2)}B`
  if (abs >= 1_000_000) return `${neg}${sign}${(abs / 1_000_000).toFixed(2)}M`
  if (abs >= 1_000) return `${neg}${sign}${(abs / 1_000).toFixed(1)}K`

  // small money values — full precision
  if (money) return `${neg}$${abs.toFixed(2)}`

  // small numbers — locale formatting for ints, 2dp for floats
  if (Number.isInteger(value)) return value.toLocaleString()
  return value.toFixed(2)
}

// drop the file extension from a filename (used for nice citation labels)
export function stripExt(name) {
  return name.replace(/\.[^/.]+$/, '')
}
