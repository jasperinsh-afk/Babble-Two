import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/endpoints'
import { TabBar } from '@/components/chrome'
import DayScheduleForm from '@/components/DayScheduleForm'
import SchoolCountdown from '@/components/SchoolCountdown'
import {
  DayCalendarIcon,
  DayChevronIcon,
  DayListIcon,
  DayPlusIcon,
} from '@/components/DayIcons'
import { toast } from '@/utils/feedback'
import {
  formatDayDate,
  readSchedules,
  relativeDayText,
  shortDayDate,
  toDateKey,
  writeSchedules,
  type DaySchedule,
} from '@/utils/days'

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

type ViewMode = 'calendar' | 'list'

interface CalendarCell {
  date: string
  day: number
  outside: boolean
}

function buildCalendar(cursor: Date): CalendarCell[] {
  const year = cursor.getFullYear()
  const month = cursor.getMonth()
  const first = new Date(year, month, 1, 12)
  const start = new Date(year, month, 1 - first.getDay(), 12)
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    return {
      date: toDateKey(date),
      day: date.getDate(),
      outside: date.getMonth() !== month,
    }
  })
}

function ScheduleCard({ schedule, onClick }: { schedule: DaySchedule; onClick: () => void }) {
  return (
    <button type="button" className="day-schedule" onClick={onClick}>
      <span className="day-schedule__marker" />
      <span className="day-schedule__content">
        <strong>{schedule.title}</strong>
        <time dateTime={schedule.date}>{shortDayDate(schedule.date)}</time>
        {schedule.note ? <span className="day-schedule__note">{schedule.note}</span> : null}
      </span>
      <span className="day-schedule__relative">{relativeDayText(schedule.date)}</span>
      <DayChevronIcon className="day-schedule__chevron" />
    </button>
  )
}

export default function Days() {
  const navigate = useNavigate()
  const today = toDateKey(new Date())
  const [schedules, setSchedules] = useState<DaySchedule[]>(() => readSchedules())
  const [view, setView] = useState<ViewMode>('calendar')
  const [cursor, setCursor] = useState(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1, 12)
  })
  const [selectedDate, setSelectedDate] = useState(today)
  const [formOpen, setFormOpen] = useState(false)

  const eventDates = useMemo(() => new Set(schedules.map((schedule) => schedule.date)), [schedules])
  const calendar = useMemo(() => buildCalendar(cursor), [cursor])
  const visibleSchedules = useMemo(
    () => view === 'list' ? schedules : schedules.filter((schedule) => schedule.date === selectedDate),
    [schedules, selectedDate, view],
  )
  const closeForm = useCallback(() => setFormOpen(false), [])

  useEffect(() => {
    let active = true
    api.daysList({ silent: true, noRetry: true })
      .then(({ list }) => {
        if (!active || !Array.isArray(list) || !list.length) return
        setSchedules((current) => {
          const merged = new Map(current.map((item) => [item.id, item]))
          for (const item of list) {
            const existing = merged.get(item.id)
            if (!existing || item.createdAt < existing.createdAt) merged.set(item.id, item)
          }
          const next = Array.from(merged.values()).sort(
            (a, b) => a.date.localeCompare(b.date) || a.createdAt - b.createdAt,
          )
          if (next.length !== current.length) writeSchedules(next)
          return next
        })
      })
      .catch(() => {})
    return () => { active = false }
  }, [])

  function shiftMonth(offset: number) {
    const next = new Date(cursor.getFullYear(), cursor.getMonth() + offset, 1, 12)
    setCursor(next)
    setSelectedDate(toDateKey(next))
  }

  function goToday() {
    const now = new Date()
    setCursor(new Date(now.getFullYear(), now.getMonth(), 1, 12))
    setSelectedDate(toDateKey(now))
  }

  function selectDate(cell: CalendarCell) {
    if (cell.outside) {
      const [year, month] = cell.date.split('-').map(Number)
      setCursor(new Date(year, month - 1, 1, 12))
    }
    setSelectedDate(cell.date)
  }

  function saveSchedule(schedule: DaySchedule) {
    const next = [...schedules, schedule].sort(
      (a, b) => a.date.localeCompare(b.date) || a.createdAt - b.createdAt,
    )
    try {
      writeSchedules(next)
      setSchedules(next)
      setSelectedDate(schedule.date)
      const [year, month] = schedule.date.split('-').map(Number)
      setCursor(new Date(year, month - 1, 1, 12))
      setFormOpen(false)
      toast('日子已保存')
      void api.daysSave(schedule).catch(() => {})
      void api.leaderboardTrackSchedule(schedule.id).catch(() => {})
    } catch {
      toast('保存失败，请检查浏览器存储权限')
    }
  }

  return (
    <div className="page page--days">
      <header className="days-header">
        <div><h1>日子</h1></div>
        <button type="button" className="days-add" onClick={() => setFormOpen(true)}>
          <DayPlusIcon />
          <span>添加日程</span>
        </button>
      </header>

      <main className="days-main">
        <SchoolCountdown />

        <div className="days-toolbar">
          <div>
            <h2>我的日程</h2>
            <span>{schedules.length ? `${schedules.length} 个被记住的日子` : '从第一个日子开始'}</span>
          </div>
          <div className="days-view-switch" role="group" aria-label="日程外观">
            <button
              type="button"
              className={view === 'calendar' ? 'is-active' : ''}
              aria-pressed={view === 'calendar'}
              onClick={() => setView('calendar')}
            >
              <DayCalendarIcon />
              日历
            </button>
            <button
              type="button"
              className={view === 'list' ? 'is-active' : ''}
              aria-pressed={view === 'list'}
              onClick={() => setView('list')}
            >
              <DayListIcon />
              列表
            </button>
          </div>
        </div>

        {view === 'calendar' ? (
          <section className="days-calendar" aria-label="日程日历">
            <div className="days-calendar__header">
              <button type="button" aria-label="上一月" onClick={() => shiftMonth(-1)}>⬅️</button>
              <strong>{cursor.getFullYear()}年 {cursor.getMonth() + 1}月</strong>
              <button type="button" aria-label="下一月" onClick={() => shiftMonth(1)}>➡️</button>
              <button type="button" className="days-calendar__today" onClick={goToday}>今天</button>
            </div>
            <div className="days-calendar__weekdays">
              {WEEKDAYS.map((weekday) => <span key={weekday}>{weekday}</span>)}
            </div>
            <div className="days-calendar__grid">
              {calendar.map((cell) => (
                <button
                  type="button"
                  key={cell.date}
                  className={[
                    'days-calendar__day',
                    cell.outside ? 'is-outside' : '',
                    cell.date === today ? 'is-today' : '',
                    cell.date === selectedDate ? 'is-selected' : '',
                    eventDates.has(cell.date) ? 'has-event' : '',
                  ].filter(Boolean).join(' ')}
                  aria-label={`${formatDayDate(cell.date)}${eventDates.has(cell.date) ? '，有日程' : ''}`}
                  aria-pressed={cell.date === selectedDate}
                  onClick={() => selectDate(cell)}
                >
                  <span>{cell.day}</span>
                  {eventDates.has(cell.date) ? <i /> : null}
                </button>
              ))}
            </div>
          </section>
        ) : null}

        <section className="days-schedules" aria-labelledby="days-schedules-title">
          <div className="days-schedules__heading">
            <h3 id="days-schedules-title">
              {view === 'list' ? '全部日程' : selectedDate === today ? '今天的日子' : shortDayDate(selectedDate)}
            </h3>
            {view === 'calendar' ? <span>{visibleSchedules.length} 项</span> : null}
          </div>
          <div className="days-schedules__list">
            {visibleSchedules.map((schedule) => (
              <ScheduleCard
                key={schedule.id}
                schedule={schedule}
                onClick={() => navigate(`/days/${encodeURIComponent(schedule.id)}`)}
              />
            ))}
          </div>
          {!visibleSchedules.length ? (
            <div className="days-empty">
              <span className="days-empty__icon"><DayCalendarIcon /></span>
              <strong>{view === 'list' ? '还没有日程' : '这一天还没有安排'}</strong>
              <p>{view === 'list' ? '点击添加日程' : '为这一天添加日程'}</p>
              <button type="button" onClick={() => setFormOpen(true)}>
                <DayPlusIcon /> 添加日程
              </button>
            </div>
          ) : null}
        </section>
      </main>

      <DayScheduleForm
        open={formOpen}
        initialDate={selectedDate || today}
        onClose={closeForm}
        onSave={saveSchedule}
      />
      <TabBar />
    </div>
  )
}
