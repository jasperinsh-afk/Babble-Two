const { call } = require('../../utils/api')
const { withShare } = require('../../utils/share')
const { dayDifference, shortDayDate, readSchedules } = require('../../utils/days')

Page(withShare({
  data: {
    todayLabel: '',
    nextSchedule: null,
    upcoming: [],
    talents: [],
    unread: 0,
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 0 })
    this.refreshSchedules()
    this.loadNotifications()
    this.loadTalents()
  },

  onPullDownRefresh() {
    this.refreshSchedules()
    Promise.all([this.loadNotifications(), this.loadTalents()]).finally(() => wx.stopPullDownRefresh())
  },

  refreshSchedules() {
    const now = new Date()
    const weekdays = ['日', '一', '二', '三', '四', '五', '六']
    const upcoming = readSchedules()
      .map(item => ({ ...item, difference: dayDifference(item.date, now) }))
      .filter(item => item.difference >= 0)
      .sort((a, b) => a.difference - b.difference || a.createdAt - b.createdAt)
      .slice(0, 4)
      .map(item => ({ ...item, dateText: shortDayDate(item.date) }))
    this.setData({
      todayLabel: `${now.getMonth() + 1}月${now.getDate()}日 周${weekdays[now.getDay()]}`,
      nextSchedule: upcoming[0] || null,
      upcoming,
    })
  },

  async loadNotifications() {
    try {
      const data = await call('me', 'messages', {}, { silent: true, noRetry: true })
      this.setData({ unread: data.unread || 0 })
    } catch (error) {}
  },

  async loadTalents() {
    try {
      const data = await call('leaderboard', 'weekly', {}, { silent: true, noRetry: true })
      this.setData({ talents: (data.list || []).slice(0, 3) })
    } catch (error) {}
  },

  goDays() {
    wx.switchTab({ url: '/pages/days/index/index' })
  },

  goCreate() {
    wx.navigateTo({ url: '/pages/day-create/index/index' })
  },

  goCountdown() {
    wx.switchTab({ url: '/pages/message/index/index' })
  },

  goLeaderboard() {
    wx.navigateTo({ url: '/pages/leaderboard/index/index' })
  },

  goNotifications() {
    wx.navigateTo({ url: '/pages/notifications/index/index' })
  },

  goCalendar() {
    wx.navigateTo({ url: '/pages/calendar/index/index' })
  },

  goDetail(event) {
    const id = event.currentTarget.dataset.id
    if (id) wx.navigateTo({ url: `/pages/day-detail/index/index?id=${encodeURIComponent(id)}` })
  },
}, {
  title: '叭啦·过日子',
  path: '/pages/index/index',
  query: '',
}))
