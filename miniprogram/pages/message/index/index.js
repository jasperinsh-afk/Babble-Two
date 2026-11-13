const { withShare } = require('../../../utils/share')
const {
  dayDifference,
  shortDayDate,
  readSchedules,
  getSchoolCountdown,
  readSchoolMode,
  writeSchoolMode,
} = require('../../../utils/days')
const { readCachedRemoteDays, loadRemoteDays } = require('../../../utils/remoteDays')
const { buildCountdownQuery } = require('../../../utils/dayShare')

const MODE_OPTIONS = [
  { mode: 'normal', label: '正常放学', time: '15:20', desc: '按常规作息放学' },
  { mode: 'bus', label: '延时校车', time: '18:10', desc: '等延时校车时使用' },
  { mode: 'study', label: '晚自习', time: '18:15', desc: '上晚自习时使用' },
]

Page(withShare({
  _timer: null,

  data: {
    countdown: { title: '', subtitle: '', mode: 'school', units: [], label: '正常放学', endText: '15:20', selectable: true },
    upcoming: [],
    nextSchedule: null,
    empty: true,
    remoteItems: [],
    showModePicker: false,
    schoolMode: 'normal',
    modeOptions: [],
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 2 })
    this.syncMode()
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
      countdown: getSchoolCountdown(now, readSchoolMode()),
      upcoming,
      nextSchedule: upcoming[0] || null,
      empty: upcoming.length === 0,
    })
  },

  syncMode() {
    const schoolMode = readSchoolMode()
    this.setData({
      schoolMode,
      modeOptions: MODE_OPTIONS.map(item => ({ ...item, selected: item.mode === schoolMode })),
    })
  },

  openModePicker() {
    if (!this.data.countdown.selectable) {
      wx.showToast({ title: '周五固定 14:40 放学', icon: 'none' })
      return
    }
    this.setData({ showModePicker: true })
  },

  closeModePicker() {
    this.setData({ showModePicker: false })
  },

  chooseMode(event) {
    const mode = event.currentTarget.dataset.mode
    if (!MODE_OPTIONS.some(item => item.mode === mode)) return
    writeSchoolMode(mode)
    this.syncMode()
    this.setData({ showModePicker: false })
    this.refresh()
  },

  noop() {},

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
