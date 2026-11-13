const { call } = require('../../../utils/api')
const { fromNowText } = require('../../../utils/format')
const { ACTION_MESSAGE_TYPES, messageTargetPath, messageTypeLabel } = require('../../../utils/messages')
const { withShare } = require('../../../utils/share')

Page(withShare({
  data: { loading: true, list: [], unread: 0 },

  onLoad() {
    this.load()
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: -1 })
  },

  onPullDownRefresh() {
    this.load().finally(() => wx.stopPullDownRefresh())
  },

  async load() {
    this.setData({ loading: true })
    try {
      const res = await call('me', 'messages')
      const list = (res.list || [])
        .filter(item => ACTION_MESSAGE_TYPES.includes(item.type))
        .map(item => ({
          ...item,
          timeText: fromNowText(item.createdAt),
          typeLabel: messageTypeLabel(item.type),
        }))
      this.setData({ list, unread: res.unread || 0 })
    } catch (error) {
      console.warn('[notifications] 加载失败', error)
    } finally {
      this.setData({ loading: false })
    }
  },

  async goMessage(event) {
    const id = event.currentTarget.dataset.id
    const message = this.data.list.find(item => item._id === id)
    if (!message) return
    if (!message.readAt) {
      try {
        await call('me', 'markRead', { ids: [message._id] }, { silent: true })
        this.setData({
          list: this.data.list.map(item => item._id === id ? { ...item, readAt: new Date().toISOString() } : item),
          unread: Math.max(0, this.data.unread - 1),
        })
      } catch (error) {}
    }
    const target = messageTargetPath(message)
    if (target) wx.navigateTo({ url: target }).catch(() => wx.switchTab({ url: target }))
  },

  async markAllRead() {
    if (!this.data.unread) return
    try {
      await call('me', 'markRead', { all: true })
      const readAt = new Date().toISOString()
      this.setData({
        list: this.data.list.map(item => ({ ...item, readAt: item.readAt || readAt })),
        unread: 0,
      })
      wx.showToast({ title: '已全部已读', icon: 'success' })
    } catch (error) {}
  },
}, {
  title: '叭啦消息通知',
  path: '/pages/notifications/index/index',
  query: '',
}))
