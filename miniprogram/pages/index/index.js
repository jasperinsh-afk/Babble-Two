const { call } = require('../../utils/api')
const { countdownText } = require('../../utils/format')
const { getHomeFeed, cacheHomeFeed } = require('../../utils/storage')

Page({
  data: {
    loading: true,
    banners: [],
    todayPoll: null,
    hotPolls: [],
    events: [],
    clubs: [],
  },

  onLoad() {
    const cached = getHomeFeed()
    if (cached) {
      this.setData({ ...this.normalize(cached), loading: false })
    }
    this.loadFeed()
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 0 })
  },

  onPullDownRefresh() {
    this.loadFeed().finally(() => wx.stopPullDownRefresh())
  },

  async loadFeed() {
    try {
      const data = await call('home', 'feed', {}, { silent: true })
      if (!data) return
      const normalized = this.normalize(data)
      cacheHomeFeed(data)
      this.setData({ ...normalized, loading: false })
    } catch (e) {
      // 失败时仍保留骨架屏/缓存，避免白屏
    }
  },

  normalize(data) {
    return {
      banners: data.banners || [],
      todayPoll: data.todayPoll
        ? { ...data.todayPoll, timeText: countdownText(data.todayPoll.endAt) }
        : null,
      hotPolls: data.hotPolls || [],
      events: data.events || [],
      clubs: data.clubs || [],
    }
  },

  onBannerTap(e) {
    const item = e.currentTarget.dataset.item
    if (item.targetRoute) {
      wx.navigateTo({ url: item.targetRoute }).catch(() => wx.switchTab({ url: item.targetRoute }))
    }
  },

  goVote(e) {
    const id = e.currentTarget.dataset.id
    wx.navigateTo({ url: `/pages/vote/detail/detail?id=${id}` })
  },

  goVoteList() {
    wx.navigateTo({ url: '/pages/vote/list/list' })
  },

  goClubList() {
    wx.navigateTo({ url: '/pages/club/list/list' })
  },

  goCalendar() {
    wx.navigateTo({ url: '/pages/calendar/index/index' })
  },

  goLiving() {
    wx.navigateTo({ url: '/pages/living/index/index' })
  },

  goScan() {
    wx.navigateTo({ url: '/pages/scan/index/index' })
  },

  goEvent(e) {
    wx.navigateTo({ url: `/pages/calendar/index/index?eventId=${e.currentTarget.dataset.id}` })
  },

  goClub(e) {
    wx.navigateTo({ url: `/pages/club/detail/detail?id=${e.currentTarget.dataset.id}` })
  },

  onShareAppMessage() {
    return {
      title: '叭啦 Babble · 身边的讨论与投票',
      path: '/pages/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
