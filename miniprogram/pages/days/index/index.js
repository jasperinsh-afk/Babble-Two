const {
  toDateKey,
  isDateKey,
  shortDayDate,
  relativeDayText,
  readSchedules,
  writeSchedules,
  sanitizeSchedules,
  migrateLocalSchedules,
  readPendingSchedules,
  removePendingSchedule,
  readDeletedIds,
  LAST_CREATED_KEY,
} = require('../../../utils/days')
const { withShare } = require('../../../utils/share')
const { call } = require('../../../utils/api')
const { readCachedRemoteDays, loadRemoteDays } = require('../../../utils/remoteDays')
const { buildCountdownQuery } = require('../../../utils/dayShare')

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

function buildCalendar(year, month, selectedDate, today, eventDates) {
  const first = new Date(year, month - 1, 1, 12)
  const start = new Date(year, month - 1, 1 - first.getDay(), 12)
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    const dateKey = toDateKey(date)
    return {
      date: dateKey,
      day: date.getDate(),
      outside: date.getMonth() !== month - 1,
      isToday: dateKey === today,
      isSelected: dateKey === selectedDate,
      hasEvent: eventDates.has(dateKey),
    }
  })
}

Page(withShare({
  data: {
    weekdays: WEEKDAYS,
    today: '',
    selectedDate: '',
    year: 2026,
    month: 1,
    view: 'calendar',
    schedules: [],
    visibleSchedules: [],
    visibleEmpty: true,
    calendarDays: [],
    remoteItems: [],
  },

  onLoad() {
    const now = new Date()
    const today = toDateKey(now)
    this.setData({
      today,
      selectedDate: today,
      year: now.getFullYear(),
      month: now.getMonth() + 1,
    }, () => this.refreshSchedules())
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 1 })
    this.applyLastCreated()
    if (this.data.today) this.refreshSchedules()
    this.syncMyDays()
    this.syncRemote()
  },

  applyLastCreated() {
    let date = ''
    try {
      date = wx.getStorageSync(LAST_CREATED_KEY) || ''
    } catch (error) {
      date = ''
    }
    if (!isDateKey(date)) return
    const parsed = new Date(`${date}T12:00:00`)
    this.setData({
      selectedDate: date,
      year: parsed.getFullYear(),
      month: parsed.getMonth() + 1,
    })
    try {
      wx.setStorageSync(LAST_CREATED_KEY, '')
    } catch (error) {
      console.warn('[days] 清除新建标记失败', error)
    }
  },

  onPullDownRefresh() {
    this.refreshSchedules()
    this.syncMyDays()
    this.syncRemote()
    wx.stopPullDownRefresh()
  },

  refreshSchedules() {
    const now = new Date()
    const local = readSchedules().map(item => ({ ...item, source: 'local' }))
    const remote = this.data.remoteItems.map(item => ({ ...item, createdAt: 0 }))
    const schedules = local.concat(remote)
      .sort((a, b) => a.date.localeCompare(b.date) || a.createdAt - b.createdAt)
      .map(item => ({
        ...item,
        shortDate: shortDayDate(item.date),
        relativeText: relativeDayText(item.date, now),
      }))
    const { view, selectedDate, year, month, today } = this.data
    const visibleSchedules = view === 'list'
      ? schedules
      : schedules.filter(item => item.date === selectedDate)
    const eventDates = new Set(schedules.map(item => item.date))
    this.setData({
      schedules,
      visibleSchedules,
      visibleEmpty: visibleSchedules.length === 0,
      calendarDays: buildCalendar(year, month, selectedDate, today, eventDates),
    })
  },

  syncMyDays() {
    migrateLocalSchedules()
    const deleted = new Set(readDeletedIds())
    const pending = readPendingSchedules().filter(item => !deleted.has(item.id))
    // 上次保存未成功的日程补传云端，成功后出队
    pending.forEach(item => {
      call('days', 'save', {
        id: item.id,
        title: item.title,
        date: item.date,
        note: item.note,
        createdAt: item.createdAt,
      }, { silent: true, noRetry: true })
        .then(() => removePendingSchedule(item.id))
        .catch(() => {})
    })
    call('days', 'list', {}, { silent: true, noRetry: true }).then(data => {
      // 云函数未部署 / 返回异常结构 / 离线：保留本地数据，绝不覆盖
      if (!data || !Array.isArray(data.list)) return
      const keyOf = item => `${item.title}|${item.date}|${item.note}|${item.createdAt}`
      const byId = new Map()
      const seen = new Set()
      // 云端为准；历史遗留的自动 _id 记录按内容去重，避免同一日程重复显示
      sanitizeSchedules(data.list).forEach(item => {
        if (deleted.has(item.id)) return
        const key = keyOf(item)
        if (seen.has(key)) return
        seen.add(key)
        byId.set(item.id, item)
      })
      // 仅补充尚未同步成功的新增，云端已删的非待同步条目随之消失
      pending.forEach(item => {
        if (byId.has(item.id) || seen.has(keyOf(item))) return
        seen.add(keyOf(item))
        byId.set(item.id, item)
      })
      writeSchedules(Array.from(byId.values()))
      this.refreshSchedules()
    }).catch(() => {})
  },

  syncRemote() {
    this.setData({ remoteItems: readCachedRemoteDays() }, () => this.refreshSchedules())
    loadRemoteDays().then(items => {
      this.setData({ remoteItems: items }, () => this.refreshSchedules())
    }).catch(() => {})
  },

  switchView(event) {
    const view = event.currentTarget.dataset.view
    if (view !== 'calendar' && view !== 'list') return
    this.setData({ view }, () => this.refreshSchedules())
  },

  shiftMonth(event) {
    const offset = Number(event.currentTarget.dataset.offset)
    const next = new Date(this.data.year, this.data.month - 1 + offset, 1, 12)
    this.setData({
      year: next.getFullYear(),
      month: next.getMonth() + 1,
      selectedDate: toDateKey(next),
    }, () => this.refreshSchedules())
  },

  goToday() {
    const now = new Date()
    this.setData({
      year: now.getFullYear(),
      month: now.getMonth() + 1,
      selectedDate: toDateKey(now),
    }, () => this.refreshSchedules())
  },

  selectDate(event) {
    const date = event.currentTarget.dataset.date
    if (!isDateKey(date)) return
    const parsed = new Date(`${date}T12:00:00`)
    this.setData({
      selectedDate: date,
      year: parsed.getFullYear(),
      month: parsed.getMonth() + 1,
    }, () => this.refreshSchedules())
  },

  openAdd() {
    const date = this.data.selectedDate || this.data.today
    wx.navigateTo({ url: `/pages/day-create/index/index?date=${encodeURIComponent(date)}` })
  },

  goDetail(event) {
    const { id, source } = event.currentTarget.dataset
    if (!id) return
    if (source && source !== 'local') {
      const item = this.data.remoteItems.find(entry => entry.id === id)
      if (item) {
        wx.navigateTo({ url: `/pages/countdown-detail/index/index?${buildCountdownQuery(item)}` })
      }
      return
    }
    wx.navigateTo({ url: `/pages/day-detail/index/index?id=${encodeURIComponent(id)}` })
  },
}, {
  title: '叭啦·日子',
  path: '/pages/days/index/index',
  query: '',
}))
