const { serviceOpened, CAMPUS_SERVICES, LIVING_VIEW_TAB, findService } = require('../../../utils/services')

/**
 * 「生活」Tab：投票以外的校园功能入口
 * （活动日历 / 社团广场 / 生活圈 / 失物招领 / 扫码打卡）
 * 当前校区未开放，整页由磨砂玻璃挡板遮住，文案「校区未开放该服务 敬请期待」。
 */
const { withShare } = require('../../../utils/share')

Page(withShare({
  data: {
    services: CAMPUS_SERVICES,
    serviceOpened,
    // -1 表示展示聚合墙；0/1 对应生活圈 / 失物招领
    subViewTab: -1,
  },

  onLoad(options) {
    const view = options.view
    if (!view || LIVING_VIEW_TAB[view] === undefined) return
    if (serviceOpened) this.setData({ subViewTab: LIVING_VIEW_TAB[view] })
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: -1 })
  },

  onPullDownRefresh() {
    if (this.data.subViewTab >= 0) {
      this.selectComponent('#living').reload()
    }
    wx.stopPullDownRefresh()
  },

  /** 开通后生效：进入子服务或跳转真实页面 */
  onServiceTap(e) {
    if (!serviceOpened) return
    const service = findService(e.currentTarget.dataset.key)
    if (!service) return
    if (service.mode === 'living') {
      this.setData({ subViewTab: LIVING_VIEW_TAB[service.view] })
    } else {
      wx.navigateTo({ url: service.path })
    }
  },

  goVoteList() {
    wx.switchTab({ url: '/pages/vote/list/list' })
  },

  onShareAppMessage() {
    return {
      title: '校园生活服务，一站式入口',
      path: '/pages/living/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
}))
