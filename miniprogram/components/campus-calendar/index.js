const { call } = require('../../utils/api')
const { dateText, dateTimeText } = require('../../utils/format')

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

Component({
  options: {
    styleIsolation: 'apply-shared',
  },
  properties: {
    eventId: {
      type: String,
      value: '',
    },
  },
  data: {
    weekdays: WEEKDAYS,
    year: 0,
    month: 0,
    days: [],
    selectedDate: '',
    eventMap: {},
    allEvents: [],
    currentEvents: [],
  },

  lifetimes: {
    attached() {
      const now = new Date()
      this.setData(
        {
          year: now.getFullYear(),
          month: now.getMonth() + 1,
          selectedDate: this.properties.eventId ? '' : dateText(now),
        },
        () => this.load()
      )
    },
  },

  methods: {
    async load() {
      const { year, month } = this.data
      try {
        const res = await call('event', 'calendar', { year, month })
        const eventMap = {}
        ;(res.events || []).forEach((e) => {
          const key = dateText(e.startAt)
          if (!eventMap[key]) eventMap[key] = []
          eventMap[key].push(e)
        })
        this.setData({
          allEvents: res.events || [],
          eventMap,
        })
        this.buildDays()
        this.updateCurrentEvents()
      } catch (e) {
        wx.showToast({ title: '加载失败', icon: 'none' })
      }
    },

    buildDays() {
      const { year, month, eventMap } = this.data
      const firstDay = new Date(year, month - 1, 1)
      const lastDay = new Date(year, month, 0)
      const startWeekday = firstDay.getDay()
      const totalDays = lastDay.getDate()

      const today = dateText(new Date())
      const days = []

      const prevLastDay = new Date(year, month - 1, 0)
      for (let i = startWeekday - 1; i >= 0; i -= 1) {
        const d = prevLastDay.getDate() - i
        days.push({ day: d, date: '', outside: true })
      }

      for (let d = 1; d <= totalDays; d += 1) {
        const date = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
        days.push({
          day: d,
          date,
          outside: false,
          isToday: date === today,
          hasEvent: !!(eventMap[date] && eventMap[date].length),
        })
      }

      const remain = 42 - days.length
      for (let d = 1; d <= remain; d += 1) {
        days.push({ day: d, date: '', outside: true })
      }

      this.setData({ days })
    },

    prevMonth() {
      let { year, month } = this.data
      month -= 1
      if (month < 1) {
        month = 12
        year -= 1
      }
      this.setData({ year, month }, () => this.load())
    },

    nextMonth() {
      let { year, month } = this.data
      month += 1
      if (month > 12) {
        month = 1
        year += 1
      }
      this.setData({ year, month }, () => this.load())
    },

    selectDate(e) {
      const date = e.currentTarget.dataset.date
      if (!date) return
      this.setData({ selectedDate: date }, () => this.updateCurrentEvents())
    },

    updateCurrentEvents() {
      const { selectedDate, eventMap, allEvents } = this.data
      if (selectedDate && eventMap[selectedDate]) {
        this.setData({ currentEvents: eventMap[selectedDate] })
        return
      }
      this.setData({ currentEvents: allEvents })
    },

    reload() {
      this.load()
    },

    goEvent(e) {
      const id = e.currentTarget.dataset.id
      const item = this.data.currentEvents.find((x) => x._id === id)
      wx.showModal({
        title: '活动报名',
        content: `${item.title}\n时间：${dateTimeText(item.startAt)}\n地点：${item.location || '待定'}`,
        confirmText: '报名',
        success: (res) => {
          if (res.confirm) this.joinEvent(id)
        },
      })
    },

    async joinEvent(id) {
      try {
        await call('event', 'join', { eventId: id })
        wx.showToast({ title: '报名成功', icon: 'success' })
        this.load()
      } catch (e) {
        /* api.js 已弹 toast */
      }
    },
  },
})
