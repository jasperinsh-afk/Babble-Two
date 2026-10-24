const { call } = require('../../utils/api')
const { messageTargetPath, messageTypeLabel } = require('../../utils/messages')
const { fromNowText } = require('../../utils/format')

// 后端 me.messages / me.markRead / me.messagePrefs 已就绪，直接读取真实数据，不写入任何假消息。
const MESSAGE_API_READY = true

const PREF_ITEMS = [
  { key: 'eventChange', label: '活动变更' },
  { key: 'eventCancel', label: '活动取消' },
  { key: 'pollResult', label: '投票结果' },
  { key: 'ownerResponse', label: '收到回复' },
  { key: 'deadline', label: '即将截止' },
]

const MESSAGE_PAGE_PATH = '/pages/message/index/index'

Page({
  data: {
    apiReady: MESSAGE_API_READY,
    prefItems: PREF_ITEMS,
    messages: [],
    cursor: '',
    hasMore: false,
    unread: 0,
    loading: false,
    loaded: false,
    prefs: null,
    savingPref: '',
  },

  onLoad() {
    this._entered = false
    this.loadMessages(true)
    this.loadPrefs()
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 2 })
    // 从详情页返回时刷新已读状态与未读数（首次进入由 onLoad 负责加载）
    if (this._entered) this.loadMessages(true)
    this._entered = true
  },

  onPullDownRefresh() {
    this.loadMessages(true).finally(() => wx.stopPullDownRefresh())
  },

  onReachBottom() {
    this.loadMore()
  },

  syncTabBadge() {
    const tabBar = this.getTabBar?.()
    if (tabBar && typeof tabBar.setBadges === 'function') {
      tabBar.setBadges({ [MESSAGE_PAGE_PATH]: this.data.unread })
    }
  },

  /** 埋点失败静默，不打断主流程 */
  trackEvent(event, props) {
    call('analytics', 'track', { event, props }, { silent: true, noRetry: true }).catch(() => {})
  },

  async loadMessages(reset) {
    if (this.data.loading) return
    const cursor = reset ? '' : this.data.cursor
    this.setData({ loading: true })
    try {
      if (!this.data.apiReady) {
        this.setData({ messages: [], cursor: '', hasMore: false, unread: 0, loaded: true })
        return
      }
      const res = await call('me', 'messages', cursor ? { cursor } : {}, { silent: true })
      const list = (res.list || []).map((item) => ({
        ...item,
        typeLabel: messageTypeLabel(item.type),
        timeText: fromNowText(item.createdAt),
      }))
      const last = list[list.length - 1]
      this.setData({
        messages: reset ? list : this.data.messages.concat(list),
        cursor: last ? last.createdAt : this.data.cursor,
        hasMore: !!res.hasMore,
        unread: res.unread || 0,
        loaded: true,
      })
      this.syncTabBadge()
    } catch (e) {
      // 失败保留空态，避免伪造数据
      this.setData({ loaded: true })
    } finally {
      this.setData({ loading: false })
    }
  },

  async loadMore() {
    if (this.data.loading || !this.data.hasMore) return
    await this.loadMessages(false)
  },

  async onMessageTap(e) {
    const id = e.currentTarget.dataset.id
    const message = this.data.messages.find((item) => item._id === id)
    if (!message) return
    const target = messageTargetPath(message)

    if (!message.readAt) {
      try {
        await call('me', 'markRead', { ids: [message._id] }, { silent: true })
        const readAt = new Date().toISOString()
        this.setData({
          messages: this.data.messages.map((item) =>
            item._id === id ? { ...item, readAt } : item,
          ),
          unread: Math.max(0, this.data.unread - 1),
        })
        this.syncTabBadge()
        this.trackEvent('message_read', {
          messageId: message._id,
          messageType: message.type,
        })
      } catch (err) {
        // 已读失败不打断跳转
      }
    }

    if (target) wx.navigateTo({ url: target })
  },

  async loadPrefs() {
    if (!this.data.apiReady) return
    try {
      const res = await call('me', 'messagePrefs', {}, { silent: true })
      this.setData({ prefs: res.prefs || null })
    } catch (e) {
      // 偏好加载失败不影响消息列表，开关保持未加载态
    }
  },

  async onPrefToggle(e) {
    const key = e.currentTarget.dataset.key
    const prefs = this.data.prefs
    if (!prefs || this.data.savingPref) return

    const previous = prefs
    const next = { ...prefs, [key]: !prefs[key] }
    // 乐观更新，失败回滚
    this.setData({ prefs: next, savingPref: key })
    try {
      const res = await call('me', 'messagePrefs', { prefs: next }, { silent: true })
      this.setData({ prefs: res.prefs || next })
      this.trackEvent('message_pref_change', { pref: key, value: next[key] })
    } catch (err) {
      this.setData({ prefs: previous })
    } finally {
      this.setData({ savingPref: '' })
    }
  },

  onShareAppMessage() {
    return {
      title: '叭啦消息中心',
      path: '/pages/message/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
