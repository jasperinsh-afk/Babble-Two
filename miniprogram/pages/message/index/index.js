const { withShare } = require('../../../utils/share')
const {
  dayDifference,
  shortDayDate,
  readSchedules,
  getSchoolCountdown,
} = require('../../../utils/days')
const { readCachedRemoteDays, loadRemoteDays } = require('../../../utils/remoteDays')
const { buildCountdownQuery } = require('../../../utils/dayShare')

Page(withShare({
  _timer: null,

  data: {
    countdown: { title: '', subtitle: '', mode: 'school', units: [] },
    upcoming: [],
    nextSchedule: null,
    empty: true,
    remoteItems: [],
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 2 })
    this.syncRemote()
    this.refresh()
    this.startTimer()
  },

  onHide() {
    this.stopTimer()
  },

  onUnload() {
    this.stopTimer()
  },

  onPullDownRefresh() {
    this.syncRemote()
    this.refresh()
    wx.stopPullDownRefresh()
  },

  startTimer() {
    this.stopTimer()
    this._timer = setInterval(() => this.refresh(), 1000)
  },

  stopTimer() {
    if (this._timer) clearInterval(this._timer)
    this._timer = null
  },

  syncRemote() {
    this.setData({ remoteItems: readCachedRemoteDays() }, () => this.refresh())
    loadRemoteDays().then(items => {
      this.setData({ remoteItems: items }, () => this.refresh())
    }).catch(() => {})
  },

  refresh() {
    const now = new Date()
    const local = readSchedules().map(schedule => ({
      ...schedule,
      source: 'local',
      createdAt: schedule.createdAt || 0,
    }))
    const remote = this.data.remoteItems.map(item => ({ ...item, createdAt: 0 }))
    const upcoming = local.concat(remote)
      .map(item => ({ ...item, difference: dayDifference(item.date, now) }))
      .filter(item => item.difference >= 0)
      .sort((a, b) => a.difference - b.difference || a.createdAt - b.createdAt || a.title.localeCompare(b.title))
      .map(item => ({
        ...item,
        dateText: shortDayDate(item.date),
        dayCount: item.difference,
      }))
    this.setData({
      countdown: getSchoolCountdown(now),
      upcoming,
      nextSchedule: upcoming[0] || null,
      empty: upcoming.length === 0,
    })
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

  openFullscreen() {
    wx.navigateTo({ url: '/pages/countdown-detail/index/index?kind=school' })
  },

  goDays() {
    wx.switchTab({ url: '/pages/days/index/index' })
  },

  goCreate() {
    wx.navigateTo({ url: '/pages/day-create/index/index' })
  },
}, {
  title: '叭啦·倒计时',
  path: '/pages/message/index/index',
  query: '',
}))
