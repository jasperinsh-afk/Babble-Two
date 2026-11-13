const { call } = require('../../utils/api')
const { withShare } = require('../../utils/share')
const { dayDifference, shortDayDate, readSchedules } = require('../../utils/days')

const VOTE_FN = 'vote'
const DAY_MS = 86400000

/** 校历按自然日算与今天的距离；本地日程全天有效，排在当天中午 */
function dayDiffFrom(value, now) {
  const date = new Date(value)
  if (isNaN(date.getTime())) return 0
  const target = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.round((target - today) / DAY_MS)
}

function countParts(difference) {
  return {
    countText: difference > 0 ? String(difference) : '今天',
    countUnit: difference > 0 ? '天' : '',
  }
}

Page(withShare({
  data: {
    todayLabel: '',
    nextSchedule: null,
    upcoming: [],
    localUpcoming: [],
    calendarEvents: [],
    talents: [],
    unread: 0,
    announcements: [],
    recentPolls: [],
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 0 })
    this.refreshSchedules()
    this.loadNotifications()
    this.loadTalents()
    this.loadHome()
  },

  onPullDownRefresh() {
    this.refreshSchedules()
    Promise.all([this.loadNotifications(), this.loadTalents(), this.loadHome()]).finally(() => wx.stopPullDownRefresh())
  },

  refreshSchedules() {
    const now = new Date()
    const weekdays = ['日', '一', '二', '三', '四', '五', '六']
    const localUpcoming = readSchedules()
      .map(item => {
        const difference = dayDifference(item.date, now)
        const stamp = new Date(`${item.date}T12:00:00`).getTime()
        return {
          ...item,
          kind: 'local',
          badge: '',
          difference,
          dateText: shortDayDate(item.date),
          eyebrow: '下一个特别的日子',
          link: '点击查看分享页 ›',
          timestamp: isNaN(stamp) ? 0 : stamp,
          ...countParts(difference),
        }
      })
      .filter(item => item.difference >= 0)
      .sort((a, b) => a.difference - b.difference || a.createdAt - b.createdAt)
    this.setData({
      todayLabel: `${now.getMonth() + 1}月${now.getDate()}日 周${weekdays[now.getDay()]}`,
      localUpcoming,
    }, () => this.mergeSchedules())
  },

  /** 校历日程与个人日程合并成同一条日程流：banner 取最近一条，列表展示前四条 */
  mergeSchedules() {
    const upcoming = (this.data.localUpcoming || [])
      .concat(this.data.calendarEvents || [])
      .filter(item => item.difference >= 0)
      .sort((a, b) => a.timestamp - b.timestamp || a.createdAt - b.createdAt || a.title.localeCompare(b.title))
      .slice(0, 4)
    this.setData({
      upcoming,
      nextSchedule: upcoming[0] || null,
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

  /** 首页聚合：公告 / 最近投票 / 校历日程。
   *  主数据源 home.feed；旧版 home 云函数没有这些字段时，用 vote.list 与 event.list 兜底。 */
  async loadHome() {
    const now = new Date()
    const dateText = (value) => {
      const d = new Date(value)
      if (isNaN(d.getTime())) return ''
      const hh = String(d.getHours()).padStart(2, '0')
      const mm = String(d.getMinutes()).padStart(2, '0')
      return `${d.getMonth() + 1}月${d.getDate()}日 ${hh}:${mm}`
    }
    const isToday = (value) => {
      const d = new Date(value)
      return !isNaN(d.getTime()) && d.toDateString() === now.toDateString()
    }
    /** 校历条目映射成与本地日程同一结构，才能进入 banner 与近期日程列表 */
    const mapCalendar = (event) => {
      const start = new Date(event.startAt)
      const valid = !isNaN(start.getTime())
      const difference = valid ? dayDiffFrom(start, now) : 0
      const location = event.location || ''
      return {
        id: event._id || '',
        title: event.title || '',
        kind: 'calendar',
        badge: '校历',
        difference,
        dateText: `${dateText(event.startAt)}${location ? ` · ${location}` : ''}`,
        eyebrow: difference > 0 ? '近期校历' : '今日校历',
        link: '查看活动日历 ›',
        timestamp: valid ? start.getTime() : 0,
        createdAt: 0,
        ...countParts(difference),
      }
    }

    let feed = null
    try {
      feed = await call('home', 'feed', {}, { silent: true, noRetry: true })
    } catch (error) {}

    const announcements = ((feed && feed.announcements) || []).slice(0, 3).map((item) => ({
      title: item.title || '',
      content: item.content || '',
      level: item.level || 'info',
      badge: item.level === 'urgent' ? '紧急公告' : item.level === 'important' ? '重要公告' : '公告',
    }))

    let polls = (feed && feed.recentPolls) || []
    if (!polls.length) {
      try {
        const res = await call(VOTE_FN, 'list', { page: 0 }, { silent: true, noRetry: true })
        polls = res.list || []
      } catch (error) {}
    }
    const recentPolls = polls.slice(0, 3).map((poll) => ({
      _id: poll._id || '',
      title: poll.title || '',
      meta: `${poll.totalVotes || 0} 人参与`,
    }))

    const calendar = feed && feed.calendarEvents
    let today = (calendar && calendar.today) || []
    let upcoming = (calendar && calendar.upcoming) || []
    if (!today.length && !upcoming.length) {
      try {
        const res = await call('event', 'list', { page: 0 }, { silent: true, noRetry: true })
        const dayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        const horizon = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
        const list = (res.list || []).filter((event) => {
          const start = new Date(event.startAt)
          return !isNaN(start.getTime()) && start >= dayStart && start <= horizon
        })
        if (list.length) {
          today = list.filter((event) => isToday(event.startAt))
          upcoming = list.filter((event) => !isToday(event.startAt))
        } else {
          // 云库里没有未来活动时不留白，展示最近录入的校历条目（带日期，用户可自行判断）
          upcoming = (res.list || []).slice(0, 3)
        }
      } catch (error) {}
    }

    this.setData({
      announcements,
      recentPolls,
      calendarEvents: today.concat(upcoming).map(mapCalendar),
    }, () => this.mergeSchedules())
  },

  /** banner 与近期日程共用同一点击入口：校历进活动日历，个人日程进分享页 */
  goSchedule(event) {
    const { kind } = event.currentTarget.dataset
    if (kind === 'calendar') return this.goEvent(event)
    return this.goDetail(event)
  },

  goPoll(event) {
    const id = event.currentTarget.dataset.id
    if (id) wx.navigateTo({ url: `/pages/vote/detail/detail?id=${encodeURIComponent(id)}` })
  },

  goVoteList() {
    wx.switchTab({ url: '/pages/vote/list/list' })
  },

  goEvent(event) {
    const id = event.currentTarget.dataset.id
    const query = id ? `?eventId=${encodeURIComponent(id)}` : ''
    wx.navigateTo({ url: `/pages/calendar/index/index${query}` })
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
