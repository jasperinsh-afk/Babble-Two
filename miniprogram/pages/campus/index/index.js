const SEGMENTS = [
  { key: 'event', label: '活动' },
  { key: 'vote', label: '投票' },
  { key: 'club', label: '社团' },
  { key: 'service', label: '服务' },
]

Page({
  data: {
    current: 'event',
    segments: SEGMENTS,
    eventId: '',
  },

  onLoad(options) {
    if (options.eventId) this.setData({ eventId: options.eventId })
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 1 })
  },

  switchSegment(e) {
    const key = e.currentTarget.dataset.key
    if (this.data.current === key) return
    this.setData({ current: key })
  },

  onShareAppMessage() {
    return {
      title: '校园活动、投票、社团与服务',
      path: '/pages/campus/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
