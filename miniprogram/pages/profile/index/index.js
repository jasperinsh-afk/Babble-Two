const { call } = require('../../../utils/api')
const { badgeRuleLabel } = require('../../../utils/config')
const { fromNowText, dateText } = require('../../../utils/format')

const { withShare } = require('../../../utils/share')

Page(withShare({
  data: {
    loading: true,
    stats: {},
    badges: [],
    recentVotes: [],
    recentCheckins: [],
    talent: null,
  },

  onLoad() {
    this.load()
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 4 })
    this.loadTalent()
  },

  onPullDownRefresh() {
    this.load().finally(() => wx.stopPullDownRefresh())
  },

  async load() {
    this.setData({ loading: true })
    try {
      const data = await call('me', 'overview')
      this.setData({
        stats: data.stats,
        badges: data.badges || [],
        recentVotes: (data.recentVotes || []).map((v) => ({
          ...v,
          createdAt: fromNowText(v.createdAt) || dateText(v.createdAt),
        })),
        recentCheckins: (data.recentCheckins || []).map((c) => ({
          ...c,
          lastTapAt: fromNowText(c.lastTapAt) || dateText(c.lastTapAt),
        })),
      })
    } catch (e) {
      console.warn('[profile] 加载失败', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  ruleText(rule) {
    if (!rule || !rule.type) return ''
    const label = badgeRuleLabel[rule.type] || rule.type
    return `${label} ≥ ${rule.count || 0}`
  },

  earnedAtText(ts) {
    if (!ts) return ''
    return fromNowText(ts) || dateText(ts)
  },

  async loadTalent() {
    try {
      const talent = await call('leaderboard', 'my', {}, { silent: true, noRetry: true })
      this.setData({ talent })
    } catch (error) {}
  },

  goLeaderboard() {
    wx.navigateTo({ url: '/pages/leaderboard/index/index' })
  },

  goNotifications() {
    wx.navigateTo({ url: '/pages/notifications/index/index' })
  },

  goBind() {
    wx.navigateTo({ url: '/pages/bind/index/index' })
  },

  onShareAppMessage() {
    return {
      title: '我在叭啦的数字足迹',
      path: '/pages/profile/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
}))
