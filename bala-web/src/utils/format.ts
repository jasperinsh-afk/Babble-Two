/** 日期与数字格式化（移植自 miniprogram/utils/format.js） */

const pad = (n: number) => (n < 10 ? `0${n}` : String(n))

function toDate(value?: string | number | Date | null): Date | null {
  if (!value) return null
  const d = value instanceof Date ? value : new Date(value)
  return Number.isNaN(d.getTime()) ? null : d
}

/** Date / ISO 字符串 → YYYY-MM-DD */
export function dateText(value?: string | number | Date | null): string {
  const d = toDate(value)
  if (!d) return ''
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** Date / ISO 字符串 → MM-DD HH:mm */
export function dateTimeText(value?: string | number | Date | null): string {
  const d = toDate(value)
  if (!d) return ''
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** 距截止时间的可读文案：3天2小时 / 5小时20分 / 12分钟 / 已结束 */
export function countdownText(value?: string | number | Date | null): string {
  const d = toDate(value)
  if (!d) return ''
  const diff = d.getTime() - Date.now()
  if (diff <= 0) return '已结束'

  const day = Math.floor(diff / 86400000)
  const hour = Math.floor((diff % 86400000) / 3600000)
  const minute = Math.floor((diff % 3600000) / 60000)

  if (day > 0) return `${day}天${hour}小时`
  if (hour > 0) return `${hour}小时${minute}分`
  return `${Math.max(minute, 1)}分钟`
}

/** 相对时间：刚刚 / 5分钟前 / 3小时前 / 2天前 / 具体日期 */
export function fromNowText(value?: string | number | Date | null): string {
  const d = toDate(value)
  if (!d) return ''
  const diff = Date.now() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 7 * 86400000) return `${Math.floor(diff / 86400000)}天前`
  return dateText(d)
}

/** 价格：分 → 元字符串，null/0 表示面议 */
export function priceText(price?: number | null): string {
  if (price === null || price === undefined || price === 0) return '面议'
  return `¥${(price / 100).toFixed(2).replace(/\.00$/, '')}`
}

/** 大数字缩写：1234 → 1.2k */
export function compactNumber(n?: number | null): string {
  const v = Number(n) || 0
  if (v < 1000) return String(v)
  if (v < 10000) return `${(v / 1000).toFixed(1).replace(/\.0$/, '')}k`
  return `${(v / 10000).toFixed(1).replace(/\.0$/, '')}w`
}
