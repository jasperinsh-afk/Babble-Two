const STORAGE_KEY = 'bala.days.schedules.v1'
const LAST_CREATED_KEY = 'bala.days.lastCreated'
const PENDING_KEY = 'bala.days.pending.v1'
const DELETED_KEY = 'bala.days.deleted.v1'
const MIGRATED_KEY = 'bala.days.cloudMigrated.v1'
const SCHOOL_MODE_KEY = 'bala.days.schoolMode.v1'
const MAX_TOMBSTONES = 500
const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']
const DAY_MS = 86400000
// 放学模式：正常放学保持 15:20，延时校车 18:10，晚自习 18:15
const SCHOOL_MODES = {
  normal: { label: '正常放学', hour: 15, minute: 20 },
  bus: { label: '延时校车', hour: 18, minute: 10 },
  study: { label: '晚自习', hour: 18, minute: 15 },
}
// 周五固定单一模式：14:40 放学，过点后直接倒计时到周一上学
const FRIDAY_MODE = { label: '周五放学', hour: 14, minute: 40 }

function pad(value) {
  return String(value).padStart(2, '0')
}

function toDateKey(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function parseDateKey(value) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(year, month - 1, day, 12)
  if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) return null
  return date
}

function isDateKey(value) {
  return parseDateKey(value) !== null
}

function dayDifference(dateKey, now = new Date()) {
  const target = parseDateKey(dateKey)
  if (!target) return 0
  const targetUtc = Date.UTC(target.getFullYear(), target.getMonth(), target.getDate())
  const todayUtc = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.round((targetUtc - todayUtc) / DAY_MS)
}

function formatDayDate(dateKey) {
  const date = parseDateKey(dateKey)
  if (!date) return dateKey
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 星期${WEEKDAYS[date.getDay()]}`
}

function shortDayDate(dateKey) {
  const date = parseDateKey(dateKey)
  if (!date) return dateKey
  return `${date.getMonth() + 1}月${date.getDate()}日 周${WEEKDAYS[date.getDay()]}`
}

function relativeDayText(dateKey, now = new Date()) {
  const difference = dayDifference(dateKey, now)
  if (difference === 0) return '就是今天'
  return difference > 0 ? `还有 ${difference} 天` : `已经 ${Math.abs(difference)} 天`
}

function sortSchedules(schedules) {
  return schedules.slice().sort((a, b) => a.date.localeCompare(b.date) || a.createdAt - b.createdAt)
}

function sanitizeSchedules(list) {
  if (!Array.isArray(list)) return []
  return sortSchedules(list.filter(item => {
    return item && typeof item.id === 'string' && typeof item.title === 'string' &&
      isDateKey(item.date) && typeof item.note === 'string' && typeof item.createdAt === 'number'
  }).map(item => ({
    id: item.id,
    title: item.title.slice(0, 40),
    date: item.date,
    note: item.note.slice(0, 120),
    createdAt: item.createdAt,
  })))
}

function readSchedules() {
  try {
    return sanitizeSchedules(wx.getStorageSync(STORAGE_KEY) || [])
  } catch (error) {
    console.warn('[days] 读取本地日程失败', error)
    return []
  }
}

function writeSchedules(schedules) {
  wx.setStorageSync(STORAGE_KEY, sanitizeSchedules(schedules))
}

function createScheduleId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

/** 尚未成功写入云端的本地日程：跨设备同步时保留并重试，避免被云端列表覆盖掉 */
function readPendingSchedules() {
  try {
    return sanitizeSchedules(wx.getStorageSync(PENDING_KEY) || [])
  } catch (error) {
    return []
  }
}

function writePendingSchedules(schedules) {
  wx.setStorageSync(PENDING_KEY, sanitizeSchedules(schedules))
}

function queuePendingSchedule(schedule) {
  const pending = readPendingSchedules().filter(item => item.id !== schedule.id)
  writePendingSchedules(pending.concat(schedule))
}

function removePendingSchedule(id) {
  writePendingSchedules(readPendingSchedules().filter(item => item.id !== id))
}

/** 已删除日程的墓碑：云端删除失败或旧响应回填时，防止日程复活 */
function readDeletedIds() {
  try {
    const list = wx.getStorageSync(DELETED_KEY)
    return Array.isArray(list) ? list.filter(id => typeof id === 'string') : []
  } catch (error) {
    return []
  }
}

function addDeletedId(id) {
  if (typeof id !== 'string' || !id) return
  const ids = readDeletedIds().filter(item => item !== id)
  ids.push(id)
  wx.setStorageSync(DELETED_KEY, ids.slice(-MAX_TOMBSTONES))
}

function clearDeletedId(id) {
  wx.setStorageSync(DELETED_KEY, readDeletedIds().filter(item => item !== id))
}

/** 一次性迁移：历史本地日程补进待同步队列，避免首次云端列表为空时被清空 */
function migrateLocalSchedules() {
  try {
    if (wx.getStorageSync(MIGRATED_KEY)) return
    readSchedules().forEach(queuePendingSchedule)
    wx.setStorageSync(MIGRATED_KEY, 1)
  } catch (error) {
    console.warn('[days] 本地日程迁移失败', error)
  }
}

function isWeekday(date) {
  return date.getDay() !== 0 && date.getDay() !== 6
}

function atTime(now, hour, minute) {
  const result = new Date(now)
  result.setHours(hour, minute, 0, 0)
  return result
}

function nextSchoolStart(now) {
  for (let offset = 0; offset <= 7; offset += 1) {
    const candidate = new Date(now)
    candidate.setDate(now.getDate() + offset)
    candidate.setHours(8, 5, 0, 0)
    if (isWeekday(candidate) && candidate.getTime() > now.getTime()) return candidate
  }
  return atTime(now, 8, 5)
}

/** 用户选择的放学模式，持久化到本地；周五会临时覆盖为单一模式 */
function readSchoolMode() {
  try {
    const value = wx.getStorageSync(SCHOOL_MODE_KEY)
    return Object.prototype.hasOwnProperty.call(SCHOOL_MODES, value) ? value : 'normal'
  } catch (error) {
    return 'normal'
  }
}

function writeSchoolMode(mode) {
  if (!Object.prototype.hasOwnProperty.call(SCHOOL_MODES, mode)) return
  try {
    wx.setStorageSync(SCHOOL_MODE_KEY, mode)
  } catch (error) {
    console.warn('[days] 保存放学模式失败', error)
  }
}

function getSchoolCountdown(now = new Date(), requestedMode = 'normal') {
  const friday = now.getDay() === 5
  const variant = friday ? 'friday' : (SCHOOL_MODES[requestedMode] ? requestedMode : 'normal')
  const config = friday ? FRIDAY_MODE : SCHOOL_MODES[variant]
  const schoolStart = atTime(now, 8, 5)
  const schoolEnd = atTime(now, config.hour, config.minute)
  // 周五不区分模式：14:40 前统一倒计时到放学，过点后由 nextSchoolStart 顺延到周一 08:05
  const duringSchool = isWeekday(now) && (friday || now >= schoolStart) && now < schoolEnd
  const target = duringSchool ? schoolEnd : nextSchoolStart(now)
  const totalSeconds = Math.max(0, Math.ceil((target.getTime() - now.getTime()) / 1000))
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const isMonday = target.getDay() === 1 && toDateKey(target) !== toDateKey(now)
  const endText = `${pad(config.hour)}:${pad(config.minute)}`
  const units = []
  if (days > 0) units.push({ key: 'days', value: String(days), label: '天' })
  units.push(
    { key: 'hours', value: pad(hours), label: '时' },
    { key: 'minutes', value: pad(minutes), label: '分' },
    { key: 'seconds', value: pad(seconds), label: '秒' },
  )
  return {
    mode: duringSchool ? 'dismissal' : 'school',
    variant,
    label: config.label,
    endText,
    selectable: !friday,
    title: duringSchool ? '距离放学' : isMonday ? '距离周一上学' : '距离上学',
    subtitle: duringSchool
      ? `今天 ${endText} 放学`
      : `${target.getMonth() + 1}月${target.getDate()}日 周${WEEKDAYS[target.getDay()]} 08:05 上学`,
    totalSeconds,
    days,
    hours,
    minutes,
    seconds,
    units,
  }
}

module.exports = {
  STORAGE_KEY,
  LAST_CREATED_KEY,
  PENDING_KEY,
  DELETED_KEY,
  MIGRATED_KEY,
  SCHOOL_MODE_KEY,
  SCHOOL_MODES,
  readSchoolMode,
  writeSchoolMode,
  sanitizeSchedules,
  migrateLocalSchedules,
  readPendingSchedules,
  writePendingSchedules,
  queuePendingSchedule,
  removePendingSchedule,
  readDeletedIds,
  addDeletedId,
  clearDeletedId,
  toDateKey,
  parseDateKey,
  isDateKey,
  dayDifference,
  formatDayDate,
  shortDayDate,
  relativeDayText,
  sortSchedules,
  readSchedules,
  writeSchedules,
  createScheduleId,
  nextSchoolStart,
  getSchoolCountdown,
}
