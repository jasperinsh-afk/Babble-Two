Page({
  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: -1 })
  },

  onPullDownRefresh() {
    this.selectComponent('#clubList').reload()
    wx.stopPullDownRefresh()
  },

  onReachBottom() {
    this.selectComponent('#clubList').loadMore()
  },

  onShareAppMessage() {
    return {
      title: '找到兴趣相投的伙伴',
      path: '/pages/club/list/list',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
