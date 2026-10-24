Page({
  data: {
    eventId: '',
  },

  onLoad(options) {
    this.setData({ eventId: options.eventId || '' })
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: -1 })
  },

  onPullDownRefresh() {
    this.selectComponent('#calendar').reload()
    wx.stopPullDownRefresh()
  },

  onShareAppMessage() {
    return {
      title: '活动日历，别错过每一场',
      path: '/pages/calendar/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
