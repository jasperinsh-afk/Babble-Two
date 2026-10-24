const { call } = require('../../utils/api')
const { countdownText, dateText, fromNowText } = require('../../utils/format')
const { getHomeFeed, cacheHomeFeed } = require('../../utils/storage')
const { ACTION_MESSAGE_TYPES, messageTargetPath, messageTypeLabel } = require('../../utils/messages')

const MESSAGE_PAGE_PATH = '/pages/message/index/index'

Page({
  data: {
    loading: true,
    banners: [],
    todayPoll: null,
    hotPolls: [],
    events: [],
    clubs: [],
    actionMessages: [],
    todayEvents: [],
    unread: 0,
  },

  onLoad() {
    this._entered = false
    const cached = getHomeFeed()
    if (cached) {
      this.setData({ ...this.normalize(cached), loading: false })
    }
    this.loadFeed()
    this.loadActions()
    this.trackFeedView()
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) {
      tabBar.setData({ selected: 0 })
      this.syncMessageBadge()
      // 从其他 Tab 返回时刷新个人行动消息与未读数
      if (this._entered) this.loadActions()
    }
    this._entered = true
  },

  onPullDownRefresh() {
    this.loadFeed().finally(() => wx.stopPullDownRefresh())
  },

  /** 埋点失败静默，不打断主流程 */
  trackFeedView() {
    call('analytics', 'track', { event: 'feed_view', props: { source: 'miniprogram_home' } }, { silent: true, noRetry: true }).catch(() => {})
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
    const events = data.events || []
    const today = dateText(new Date())
    return {
      banners: data.banners || [],
      todayPoll: data.todayPoll
        ? { ...data.todayPoll, timeText: countdownText(data.todayPoll.endAt) }
        : null,
      hotPolls: data.hotPolls || [],
      events,
      clubs: data.clubs || [],
      todayEvents: events.filter((event) => dateText(event.startAt) === today),
    }
  },

  /** 个人行动数据单独来自 me.messages，不混入公共 home.feed，不伪造数据 */
  async loadActions() {
    try {
      const res = await call('me', 'messages', {}, { silent: true })
      const list = (res.list || []).map((item) => ({
        ...item,
        typeLabel: messageTypeLabel(item.type),
        timeText: fromNowText(item.createdAt),
      }))
      this.setData({
        actionMessages: list.filter((item) => ACTION_MESSAGE_TYPES.includes(item.type)),
        unread: res.unread || 0,
      })
      this.syncMessageBadge()
    } catch (e) {
      // 失败保留空态，不伪造数据
    }
  },

  syncMessageBadge() {
    const tabBar = this.getTabBar?.()
    if (tabBar && typeof tabBar.setBadges === 'function') {
      tabBar.setBadges({ [MESSAGE_PAGE_PATH]: this.data.unread })
    }
  },

  async onActionTap(e) {
    const id = e.currentTarget.dataset.id
    const message = this.data.actionMessages.find((item) => item._id === id)
    if (!message) return
    const target = messageTargetPath(message)

    if (!message.readAt) {
      try {
        await call('me', 'markRead', { ids: [message._id] }, { silent: true })
        const readAt = new Date().toISOString()
        this.setData({
          actionMessages: this.data.actionMessages.map((item) =>
            item._id === id ? { ...item, readAt } : item,
          ),
          unread: Math.max(0, this.data.unread - 1),
        })
        this.syncMessageBadge()
        this.trackEvent('message_read', {
          messageId: message._id,
          messageType: message.type,
          source: 'home_action',
        })
      } catch (err) {
        // 已读失败不打断跳转
      }
    }

    if (target) wx.navigateTo({ url: target })
  },

  trackEvent(event, props) {
    call('analytics', 'track', { event, props }, { silent: true, noRetry: true }).catch(() => {})
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
