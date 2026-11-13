const { withShare } = require('../../../utils/share')
const { getSchoolCountdown, toDateKey, formatDayDate } = require('../../../utils/days')
const {
  buildCountdownQuery,
  createCountdownImage,
  countdownUnits,
} = require('../../../utils/dayShare')

function decodeValue(value) {
  try {
    return value == null ? '' : decodeURIComponent(String(value))
  } catch (error) {
    return String(value || '')
  }
}

function safeText(value, max) {
  return decodeValue(value).trim().slice(0, max)
}

function schoolItem(now) {
  const countdown = getSchoolCountdown(now)
  return {
    title: countdown.title,
    date: toDateKey(now),
    targetAt: new Date(now.getTime() + countdown.totalSeconds * 1000).toISOString(),
    note: countdown.subtitle,
    emoji: countdown.mode === 'dismissal' ? '🏫' : '🎒',
    badge: '上下学',
    source: 'school-time',
  }
}

function fromQuery(options, now) {
  const title = safeText(options.title, 40)
  const targetAt = safeText(options.targetAt, 40)
  if (!title || !targetAt) return null
  return {
    title,
    date: safeText(options.date, 10) || toDateKey(now),
    targetAt,
    note: safeText(options.note, 120),
    emoji: safeText(options.emoji, 4) || '⏰',
    badge: safeText(options.badge, 10) || '倒计时',
    source: 'remote',
  }
}

Page(withShare({
  data: {
    item: null,
    units: { days: 0, hours: '00', minutes: '00', seconds: '00' },
    dateText: '',
    statusBarHeight: 20,
    saving: false,
    shareImagePath: '',
  },

  onLoad(options) {
    this.options = options || {}
    const now = new Date()
    const item = (this.options.shared === '1' && fromQuery(this.options, now)) || schoolItem(now)
    let statusBarHeight = 20
    try {
      const system = wx.getSystemInfoSync ? wx.getSystemInfoSync() : {}
      statusBarHeight = Number(system.statusBarHeight) || 20
    } catch (error) {
      statusBarHeight = 20
    }
    this.setData({
      item,
      statusBarHeight,
      dateText: formatDayDate(item.date),
      units: countdownUnits(item.targetAt, now),
    })
  },

  onShow() {
    this.startTimer()
  },

  onHide() {
    this.stopTimer()
  },

  onUnload() {
    this.stopTimer()
  },

  onShareAppMessage() {
    const item = this.data.item || {}
    return {
      title: `${item.title} · 还有 ${this.data.units.days} 天`,
      path: `/pages/countdown-detail/index/index?${buildCountdownQuery(item)}`,
      imageUrl: this.data.shareImagePath || '/assets/brand/share-card.png',
    }
  },

  startTimer() {
    this.stopTimer()
    this.tick()
    this.timer = setInterval(() => this.tick(), 1000)
  },

  stopTimer() {
    if (this.timer) {
      clearInterval(this.timer)
      this.timer = null
    }
  },

  tick() {
    if (!this.data.item) return
    this.setData({ units: countdownUnits(this.data.item.targetAt, new Date()) })
  },

  async saveShareImage() {
    if (this.data.saving || !this.data.item) return
    this.setData({ saving: true })
    wx.showLoading({ title: '正在生成图片', mask: true })
    try {
      const filePath = await createCountdownImage(this, this.data.item)
      this.setData({ shareImagePath: filePath })
      await new Promise((resolve, reject) => {
        wx.saveImageToPhotosAlbum({ filePath, success: resolve, fail: reject })
      })
      wx.hideLoading()
      wx.showToast({ title: '已保存到相册', icon: 'success' })
    } catch (error) {
      wx.hideLoading()
      const message = String(error && (error.errMsg || error.message) || error)
      if (message.includes('cancel')) return
      if (message.includes('auth') || message.includes('deny')) {
        wx.showModal({
          title: '需要相册权限',
          content: this.data.shareImagePath ? '可长按已生成的图片保存，或在设置中允许访问相册' : '请在设置中允许保存图片到相册',
          confirmText: '去设置',
          success: result => {
            if (result.confirm) wx.openSetting()
          },
        })
      } else if (this.data.shareImagePath) {
        wx.showModal({ title: '图片已生成', content: '请长按预览图片保存到相册', showCancel: false })
      } else {
        console.error('[countdown-detail] 分享图生成失败', error)
        wx.showToast({ title: '图片生成失败，请重试', icon: 'none' })
      }
    } finally {
      this.setData({ saving: false })
    }
  },

  goBack() {
    wx.navigateBack({ fail: () => wx.switchTab({ url: '/pages/message/index/index' }) })
  },

  noop() {},
}))
