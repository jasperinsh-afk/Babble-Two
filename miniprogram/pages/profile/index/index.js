const { call } = require('../../../utils/api')
const { badgeRuleLabel } = require('../../../utils/config')
const { fromNowText, dateText } = require('../../../utils/format')

Page({
  data: {
    loading: true,
    stats: {},
    badges: [],
    recentVotes: [],
    recentCheckins: [],
  },

  onLoad() {
    this.load()
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 4 })
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

  onShareAppMessage() {
    return {
      title: '我在叭啦的数字足迹',
      path: '/pages/profile/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
