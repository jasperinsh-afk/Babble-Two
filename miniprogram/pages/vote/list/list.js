Page({
  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: -1 })
  },

  onPullDownRefresh() {
    this.selectComponent('#voteList').reload()
    wx.stopPullDownRefresh()
  },

  onReachBottom() {
    this.selectComponent('#voteList').loadMore()
  },

  onShareAppMessage() {
    return {
      title: '来投票，用选择表达态度',
      path: '/pages/vote/list/list',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
