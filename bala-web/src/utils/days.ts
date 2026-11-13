export interface DaySchedule {
  id: string
  title: string
  date: string
  note: string
  createdAt: number
}

export interface SchoolCountdown {
  mode: 'dismissal' | 'school'
  target: Date
  title: string
  subtitle: string
  totalSeconds: number
  days: number
  hours: number
  minutes: number
  seconds: number
}

const STORAGE_KEY = 'bala.days.schedules.v1'
const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']
const DAY_MS = 86_400_000

export function toDateKey(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function parseDateKey(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return null
  const year = Number(match[1])
  const month = Number(match[2])
  const day = Number(match[3])
  const date = new Date(year, month - 1, day, 12)
  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null
  }
  return date
}

export function isDateKey(value: string): boolean {
  return parseDateKey(value) !== null
}

export function dayDifference(dateKey: string, now = new Date()): number {
  const target = parseDateKey(dateKey)
  if (!target) return 0
  const targetUtc = Date.UTC(target.getFullYear(), target.getMonth(), target.getDate())
  const todayUtc = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.round((targetUtc - todayUtc) / DAY_MS)
}

export function formatDayDate(dateKey: string): string {
  const date = parseDateKey(dateKey)
  if (!date) return dateKey
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 星期${WEEKDAYS[date.getDay()]}`
}

export function shortDayDate(dateKey: string): string {
  const date = parseDateKey(dateKey)
  if (!date) return dateKey
  return `${date.getMonth() + 1}月${date.getDate()}日 周${WEEKDAYS[date.getDay()]}`
}

export function relativeDayText(dateKey: string, now = new Date()): string {
  const difference = dayDifference(dateKey, now)
  if (difference === 0) return '就是今天'
  return difference > 0 ? `还有 ${difference} 天` : `已经 ${Math.abs(difference)} 天`
}

export function readSchedules(): DaySchedule[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
      .filter((item): item is DaySchedule => {
        if (!item || typeof item !== 'object') return false
        const schedule = item as Partial<DaySchedule>
        return (
          typeof schedule.id === 'string' &&
          typeof schedule.title === 'string' &&
          typeof schedule.date === 'string' &&
          isDateKey(schedule.date) &&
          typeof schedule.note === 'string' &&
          typeof schedule.createdAt === 'number'
        )
      })
      .map((schedule) => ({
        ...schedule,
        title: schedule.title.slice(0, 40),
        note: schedule.note.slice(0, 120),
      }))
      .sort((a, b) => a.date.localeCompare(b.date) || a.createdAt - b.createdAt)
  } catch {
    return []
  }
}

export function writeSchedules(schedules: DaySchedule[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(schedules))
}

export function createScheduleId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

function isWeekday(date: Date): boolean {
  return date.getDay() !== 0 && date.getDay() !== 6
}

function atTime(now: Date, hour: number, minute: number): Date {
  const result = new Date(now)
  result.setHours(hour, minute, 0, 0)
  return result
}

export function nextSchoolStart(now: Date): Date {
  for (let offset = 0; offset <= 7; offset += 1) {
    const candidate = new Date(now)
    candidate.setDate(now.getDate() + offset)
    candidate.setHours(8, 5, 0, 0)
    if (isWeekday(candidate) && candidate.getTime() > now.getTime()) return candidate
  }
  return atTime(now, 8, 5)
}

export function getSchoolCountdown(now = new Date()): SchoolCountdown {
  const schoolStart = atTime(now, 8, 5)
  const schoolEnd = atTime(now, 15, 20)
  const duringSchool = isWeekday(now) && now >= schoolStart && now < schoolEnd
  const target = duringSchool ? schoolEnd : nextSchoolStart(now)
  const totalSeconds = Math.max(0, Math.ceil((target.getTime() - now.getTime()) / 1000))
  const days = Math.floor(totalSeconds / 86_400)
  const hours = Math.floor((totalSeconds % 86_400) / 3_600)
  const minutes = Math.floor((totalSeconds % 3_600) / 60)
  const seconds = totalSeconds % 60
  const isMonday = target.getDay() === 1 && toDateKey(target) !== toDateKey(now)

  return {
    mode: duringSchool ? 'dismissal' : 'school',
    target,
    title: duringSchool ? '距离放学' : isMonday ? '距离周一上学' : '距离上学',
    subtitle: duringSchool
      ? '今天 15:20 放学'
      : `${target.getMonth() + 1}月${target.getDate()}日 周${WEEKDAYS[target.getDay()]} 08:05 上学`,
    totalSeconds,
    days,
    hours,
    minutes,
    seconds,
  }
}
