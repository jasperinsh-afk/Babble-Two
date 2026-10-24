Page({
  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: -1 })
  },

  onPullDownRefresh() {
    this.selectComponent('#living').reload()
    wx.stopPullDownRefresh()
  },

  onShareAppMessage() {
    return {
      title: '失物招领与二手交换，一站式搞定',
      path: '/pages/living/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
