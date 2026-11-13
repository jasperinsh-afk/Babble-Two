const { call } = require('./api')
const { toDateKey, isDateKey } = require('./days')

const STORAGE_KEY = 'bala.remote.days.v1'

function toDate(value) {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isFinite(date.getTime()) ? date : null
}

function dateKeyOf(value) {
  const date = toDate(value)
  return date ? toDateKey(date) : ''
}

function nextOccurrence(item, now = new Date()) {
  const fixed = toDate(item && item.targetAt)
  if (fixed && fixed.getTime() > now.getTime()) return fixed.toISOString()
  const time = /^([01]\d|2[0-3]):([0-5]\d)$/.exec(String((item && item.dailyTime) || ''))
  if (!time) return ''
  const raw = item && item.weekdays
  const weekdays = Array.isArray(raw) && raw.length ? raw.map(Number) : [1, 2, 3, 4, 5]
  for (let offset = 0; offset <= 14; offset += 1) {
    const candidate = new Date(now)
    candidate.setDate(now.getDate() + offset)
    candidate.setHours(Number(time[1]), Number(time[2]), 0, 0)
    if (candidate.getTime() > now.getTime() && weekdays.includes(candidate.getDay())) {
      return candidate.toISOString()
    }
  }
  return ''
}

function normalizeSchoolEvent(event, now) {
  if (!event || event.isDeleted || event.status === 'cancelled') return null
  const date = dateKeyOf(event.startAt)
  const title = String(event.title || '').trim().slice(0, 40)
  if (!isDateKey(date) || !title) return null
  const target = toDate(event.startAt)
  if (!target || target.getTime() < now.getTime() - 86400000) return null
  return {
    id: `school:${event._id || date}`,
    title,
    date,
    targetAt: target.toISOString(),
    note: String(event.location || event.description || '').trim().slice(0, 120),
    badge: '校历',
    emoji: '🏫',
    source: 'school',
  }
}

function normalizeRemoteCountdown(item, now) {
  if (!item || item.isActive === false) return null
  const title = String(item.title || '').trim().slice(0, 40)
  if (!title) return null
  const targetAt = nextOccurrence(item, now)
  if (!targetAt) return null
  return {
    id: `remote:${item._id || item.code || title}`,
    title,
    date: dateKeyOf(targetAt),
    targetAt,
    note: String(item.description || item.note || '').trim().slice(0, 120),
    badge: String(item.badge || '倒计时').slice(0, 10),
    emoji: Array.from(String(item.emoji || '⏰')).slice(0, 2).join(''),
    source: 'remote',
  }
}

function normalizeRemoteDays(data, now = new Date()) {
  const source = data || {}
  const events = Array.isArray(source.events) ? source.events : []
  const countdowns = Array.isArray(source.countdowns) ? source.countdowns : []
  const items = events.map(event => normalizeSchoolEvent(event, now))
    .concat(countdowns.map(item => normalizeRemoteCountdown(item, now)))
    .filter(item => item && isDateKey(item.date))
  const seen = new Set()
  return items
    .sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id))
    .filter(item => {
      if (seen.has(item.id)) return false
      seen.add(item.id)
      return true
    })
}

function readCachedRemoteDays() {
  try {
    const cached = wx.getStorageSync(STORAGE_KEY)
    return Array.isArray(cached) ? cached : []
  } catch (error) {
    return []
  }
}

async function loadRemoteDays() {
  try {
    const data = await call('days', 'remote', {}, { silent: true, noRetry: true })
    const items = normalizeRemoteDays(data)
    try {
      wx.setStorageSync(STORAGE_KEY, items)
    } catch (error) {
      console.warn('[remoteDays] 缓存失败', error)
    }
    return items
  } catch (error) {
    return readCachedRemoteDays()
  }
}

module.exports = {
  STORAGE_KEY,
  nextOccurrence,
  normalizeRemoteDays,
  readCachedRemoteDays,
  loadRemoteDays,
}
