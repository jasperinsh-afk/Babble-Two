const { withShare } = require('../../../utils/share')

Page(withShare({
  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: 3 })
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
      title: '叭啦·投票',
      path: '/pages/vote/list/list',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
}))
