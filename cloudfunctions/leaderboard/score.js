const POINTS = { vote: 10, schedule: 5, nickname: 5 }
const MEDAL_NAME = '榜一大哥'
const CHINA_OFFSET = 8 * 3600000
const WEEK_MS = 7 * 86400000

function weekStart(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value)
  const china = new Date(date.getTime() + CHINA_OFFSET)
  const weekday = china.getUTCDay()
  const sinceMonday = (weekday + 6) % 7
  const utcDay = Date.UTC(china.getUTCFullYear(), china.getUTCMonth(), china.getUTCDate() - sinceMonday)
  return new Date(utcDay - CHINA_OFFSET)
}

function weekKey(value = new Date()) {
  const start = weekStart(value)
  const china = new Date(start.getTime() + CHINA_OFFSET)
  return `${china.getUTCFullYear()}-${String(china.getUTCMonth() + 1).padStart(2, '0')}-${String(china.getUTCDate()).padStart(2, '0')}`
}

function previousWeekStart(value = new Date()) {
  return new Date(weekStart(value).getTime() - WEEK_MS)
}

function dayStart(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value)
  const china = new Date(date.getTime() + CHINA_OFFSET)
  return new Date(Date.UTC(china.getUTCFullYear(), china.getUTCMonth(), china.getUTCDate()) - CHINA_OFFSET)
}

function sanitizeNickname(value) {
  return String(value || '').replace(/[\x00-\x1F\x7F]/g, '').trim().slice(0, 16)
}

function aggregateRecords(records) {
  const users = {}
  records.forEach(record => {
    if (!record || !record._openid || !Number.isFinite(record.points)) return
    const openid = record._openid
    if (!users[openid]) users[openid] = { _openid: openid, points: 0, lastPointAt: 0 }
    users[openid].points += record.points
    const time = new Date(record.createdAt || 0).getTime() || 0
    users[openid].lastPointAt = Math.max(users[openid].lastPointAt, time)
  })
  return Object.values(users).sort((a, b) =>
    b.points - a.points || a.lastPointAt - b.lastPointAt || a._openid.localeCompare(b._openid),
  )
}

function rankNumber(sorted, index) {
  return index + 1
}

module.exports = {
  POINTS,
  MEDAL_NAME,
  WEEK_MS,
  weekStart,
  weekKey,
  previousWeekStart,
  dayStart,
  sanitizeNickname,
  aggregateRecords,
  rankNumber,
}
