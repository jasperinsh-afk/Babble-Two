const { call } = require('../../utils/api')

// 消息列表 UI 就绪前保持关闭；接通后改为 me.messages 分页读取，不写入任何假消息。
const MESSAGE_API_READY = false

Page({
  data: {
    messages: [],
    loading: false,
    loaded: false,
    apiReady: MESSAGE_API_READY,
  },

  onLoad() {
    this.loadMessages()
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 2 })
  },

  onPullDownRefresh() {
    this.loadMessages().finally(() => wx.stopPullDownRefresh())
  },

  async loadMessages() {
    this.setData({ loading: true })
    try {
      if (!this.data.apiReady) {
        this.setData({ messages: [], loaded: true })
        return
      }
      const res = await call('me', 'messages', {})
      this.setData({ messages: res.list || [], loaded: true })
    } catch (e) {
      wx.showToast({ title: '消息加载失败', icon: 'none' })
    } finally {
      this.setData({ loading: false })
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
