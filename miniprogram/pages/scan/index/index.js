const { call } = require('../../../utils/api')
const { rarityLabel } = require('../../../utils/config')

// 与 badges 集合中 scan_explorer 的 rule.count 保持一致
const BADGE_SCAN_THRESHOLD = 3

const LOCATION_RULES = [
  { type: 'canteen', name: '食堂', desc: '食堂入口海报，扫码参与今日午餐投票' },
  { type: 'library', name: '图书馆', desc: '图书馆一楼公告位，扫码查看读书社团' },
  { type: 'dormitory', name: '宿舍楼', desc: '各楼层电梯口，扫码进入住宿圈' },
  { type: 'bulletin', name: '公告栏', desc: '中央公告栏，扫码查看全校活动' },
  { type: 'classroom', name: '教室区', desc: '教学楼走廊，扫码参与课程相关投票' },
  { type: 'clubroom', name: '社团活动室', desc: '社团活动室门口，扫码直达社团主页' },
  { type: 'sports', name: '体育场馆', desc: '体育馆入口，扫码报名体育赛事' },
  { type: 'gateway', name: '校门', desc: '校门口迎新海报，扫码领取新手勋章' },
]

Page({
  data: {
    key: '',
    card: null,
    locationName: '',
    rules: LOCATION_RULES,
    nextBadgeNeed: BADGE_SCAN_THRESHOLD,
    newBadges: [],
  },

  onLoad(options) {
    // 小程序码冷启动 scene，或 URL query 的 cardId
    const scene = options.scene
    const cardId = options.cardId
    if (scene) {
      this.lookup(String(scene))
    } else if (cardId) {
      this.lookup(cardId)
    }
  },

  startScan() {
    wx.scanCode({
      scanType: ['qrCode'],
      success: (res) => {
        this.lookup(res.result)
      },
      fail: () => {
        wx.showToast({ title: '未扫码', icon: 'none' })
      },
    })
  },

  onInput(e) {
    this.setData({ key: e.detail.value })
  },

  manualLookup() {
    if (!this.data.key) return
    this.lookup(this.data.key)
  },

  async lookup(key) {
    if (!key) return
    try {
      const card = await call('scan', 'cardByCode', { key }, { loading: '查询中…' })
      const rule = LOCATION_RULES.find((r) => r.type === card.locationType) || {}
      this.setData({
        card,
        locationName: rule.name || card.locationType || '未知区域',
        nextBadgeNeed: Math.max(0, BADGE_SCAN_THRESHOLD - (card.uniqueCards || 0)),
        newBadges: [],
      })
    } catch (e) {
      wx.showToast({ title: e.message || '查询失败', icon: 'none' })
    }
  },

  async doCheckin() {
    const { card } = this.data
    if (!card) return
    try {
      const res = await call('scan', 'checkin', { key: card.cardId }, { loading: '打卡中…' })
      this.setData({
        newBadges: res.newBadges || [],
        'card.checked': true,
        'card.tapCount': res.firstTime ? 1 : (this.data.card.tapCount || 0) + 1,
        'card.uniqueCards': res.uniqueCards,
        nextBadgeNeed: Math.max(0, BADGE_SCAN_THRESHOLD - res.uniqueCards),
      })
      wx.showToast({ title: '打卡成功', icon: 'success' })

      if (res.target && res.target.type && res.target.id) {
        setTimeout(() => {
          if (res.target.type === 'vote') {
            wx.navigateTo({ url: `/pages/vote/detail/detail?id=${res.target.id}` })
          } else if (res.target.type === 'club') {
            wx.navigateTo({ url: `/pages/club/detail/detail?id=${res.target.id}` })
          } else if (res.target.type === 'event') {
            wx.navigateTo({ url: `/pages/calendar/index/index?eventId=${res.target.id}` })
          }
        }, 1200)
      }

      if (res.newBadges.length) {
        setTimeout(() => this.setData({ newBadges: [] }), 3000)
      }
    } catch (e) {
      wx.showToast({ title: e.message || '打卡失败', icon: 'none' })
    }
  },

  rarityText(r) {
    return rarityLabel[r] || r
  },

  onShareAppMessage() {
    return {
      title: '扫码打卡，解锁勋章',
      path: '/pages/scan/index/index',
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
