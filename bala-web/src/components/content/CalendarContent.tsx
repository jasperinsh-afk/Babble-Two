import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { EventCard } from '@/components/cards'
import { EmptyView, Modal, SectionHeader } from '@/components/common'
import { TabBar } from '@/components/chrome'
import type { EventInfo } from '@/types/models'
import { dateText, dateTimeText } from '@/utils/format'
import { toast } from '@/utils/feedback'

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

interface DayCell {
  day: number
  date: string
  outside: boolean
  isToday?: boolean
  hasEvent?: boolean
}

function buildDays(year: number, month: number, eventMap: Record<string, EventInfo[]>): DayCell[] {
  const firstDay = new Date(year, month - 1, 1)
  const totalDays = new Date(year, month, 0).getDate()
  const startWeekday = firstDay.getDay()
  const today = dateText(new Date())
  const days: DayCell[] = []

  const prevLastDay = new Date(year, month - 1, 0).getDate()
  for (let i = startWeekday - 1; i >= 0; i -= 1) {
    days.push({ day: prevLastDay - i, date: '', outside: true })
  }
  for (let d = 1; d <= totalDays; d += 1) {
    const date = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    days.push({
      day: d,
      date,
      outside: false,
      isToday: date === today,
      hasEvent: Boolean(eventMap[date]?.length),
    })
  }
  const remain = 42 - days.length
  for (let d = 1; d <= remain; d += 1) {
    days.push({ day: d, date: '', outside: true })
  }
  return days
}

export default function CalendarContent({ embedded = false }: { embedded?: boolean }) {
  const now = new Date()
  const [searchParams] = useSearchParams()
  const focusEventId = searchParams.get('eventId')
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [selectedDate, setSelectedDate] = useState(focusEventId ? '' : dateText(now))
  const [modalEvent, setModalEvent] = useState<EventInfo | null>(null)
  const queryClient = useQueryClient()

  const { data } = useQuery({
    queryKey: ['event', 'calendar', year, month],
    queryFn: () => api.eventCalendar(year, month),
  })

  const allEvents = useMemo(() => data?.events ?? [], [data])
  const eventMap = useMemo(() => {
    const map: Record<string, EventInfo[]> = {}
    allEvents.forEach((event) => {
      const key = dateText(event.startAt)
      if (!key) return
      map[key] = [...(map[key] || []), event]
    })
    return map
  }, [allEvents])

  const days = useMemo(() => buildDays(year, month, eventMap), [year, month, eventMap])
  const currentEvents = selectedDate && eventMap[selectedDate] ? eventMap[selectedDate] : allEvents

  // 从首页「推荐活动」跳入时直接打开对应活动的报名弹窗
  useEffect(() => {
    if (!focusEventId) return
    const target = allEvents.find((event) => event._id === focusEventId)
    if (target) setModalEvent(target)
  }, [focusEventId, allEvents])

  const joinMutation = useMutation({
    mutationFn: (eventId: string) => api.eventJoin(eventId),
    onSuccess: async (result) => {
      toast(result.waitlisted ? '已满员，已加入候补' : '报名成功')
      setModalEvent(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['event', 'calendar'] }),
        queryClient.invalidateQueries({ queryKey: ['home', 'feed'] }),
        queryClient.invalidateQueries({ queryKey: ['me', 'overview'] }),
      ])
    },
  })

  function shiftMonth(delta: number) {
    let nextMonth = month + delta
    let nextYear = year
    if (nextMonth < 1) {
      nextMonth = 12
      nextYear -= 1
    } else if (nextMonth > 12) {
      nextMonth = 1
      nextYear += 1
    }
    setYear(nextYear)
    setMonth(nextMonth)
  }

  return (
    <div className={`${embedded ? '' : 'page'} page--calendar`}>
      <div className="calendar-header">
        <button type="button" className="calendar-header__btn" aria-label="上一月" onClick={() => shiftMonth(-1)}>
          ‹
        </button>
        <span className="calendar-header__title">
          {year} 年 {month} 月
        </span>
        <button type="button" className="calendar-header__btn" aria-label="下一月" onClick={() => shiftMonth(1)}>
          ›
        </button>
      </div>

      <div className="calendar-weekdays">
        {WEEKDAYS.map((day) => (
          <span className="calendar-weekday" key={day}>
            {day}
          </span>
        ))}
      </div>

      <div className="calendar-grid">
        {days.map((cell, index) => (
          <button
            type="button"
            key={cell.date || `outside-${index}`}
            disabled={!cell.date}
            className={[
              'calendar-day',
              cell.outside ? 'calendar-day--outside' : '',
              cell.isToday ? 'calendar-day--today' : '',
              cell.date && cell.date === selectedDate ? 'calendar-day--selected' : '',
              cell.hasEvent ? 'calendar-day--event' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            onClick={() => cell.date && setSelectedDate(cell.date)}
          >
            <span className="calendar-day__num">{cell.day}</span>
            {cell.hasEvent ? <span className="calendar-day__dot" /> : null}
          </button>
        ))}
      </div>

      <section className="section">
        <SectionHeader title={selectedDate ? `${selectedDate} 的活动` : '近期活动'} />
        {currentEvents.map((event) => (
          <EventCard key={event._id} event={event} onClick={() => setModalEvent(event)} />
        ))}
        {!currentEvents.length ? (
          <EmptyView
            icon="🗓️"
            title="暂无活动"
            subtitle={selectedDate ? '换个日期看看' : '近期还没有活动哦'}
          />
        ) : null}
      </section>

      <Modal
        open={Boolean(modalEvent)}
        title="活动报名"
        confirmText="报名"
        onCancel={() => setModalEvent(null)}
        onConfirm={() => modalEvent && joinMutation.mutate(modalEvent._id)}
      >
        {modalEvent
          ? `${modalEvent.title}\n时间：${dateTimeText(modalEvent.startAt)}\n地点：${
              modalEvent.location || '待定'
            }`
          : ''}
      </Modal>
      {embedded ? null : <TabBar />}
    </div>
  )
}
