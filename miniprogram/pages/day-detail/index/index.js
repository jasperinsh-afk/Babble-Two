const {
  dayDifference,
  formatDayDate,
  isDateKey,
  readSchedules,
  writeSchedules,
  addDeletedId,
  clearDeletedId,
  removePendingSchedule,
} = require('../../../utils/days')
const { buildShareQuery, createScheduleImage } = require('../../../utils/dayShare')
const { withShare } = require('../../../utils/share')
const { call } = require('../../../utils/api')

function decodeValue(value) {
  const text = String(value || '')
  try {
    return decodeURIComponent(text)
  } catch (error) {
    return text
  }
}

Page(withShare({
  _dayTimer: null,

  data: {
    schedule: null,
    isShared: false,
    missing: false,
    fullDate: '',
    countLabel: '',
    dayCount: 0,
    countClass: '',
    saving: false,
    shareImagePath: '',
  },

  onLoad(options) {
    const isShared = options.shared === '1'
    let schedule = null
    if (isShared) {
      const title = decodeValue(options.title).trim().slice(0, 40)
      const date = decodeValue(options.date)
      if (title && isDateKey(date)) {
        schedule = {
          id: 'shared',
          title,
          date,
          note: decodeValue(options.note).trim().slice(0, 120),
          createdAt: 0,
        }
      }
    } else {
      const id = decodeValue(options.id)
      schedule = readSchedules().find(item => item.id === id) || null
    }
    this.setData({ schedule, isShared, missing: !schedule })
    if (schedule) this.refreshDayCount()
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: -1 })
    this.refreshDayCount()
    this._dayTimer = setInterval(() => this.refreshDayCount(), 60000)
  },

  onHide() {
    this.clearDayTimer()
  },

  onUnload() {
    this.clearDayTimer()
  },

  clearDayTimer() {
    if (this._dayTimer) clearInterval(this._dayTimer)
    this._dayTimer = null
  },

  refreshDayCount() {
    const schedule = this.data.schedule
    if (!schedule) return
    const difference = dayDifference(schedule.date, new Date())
    this.setData({
      fullDate: formatDayDate(schedule.date),
      countLabel: difference === 0 ? '就是今天' : difference > 0 ? '还有' : '已经',
      dayCount: Math.abs(difference),
      countClass: Math.abs(difference) >= 1000 ? 'is-long' : '',
    })
  },

  async saveShareImage() {
    const schedule = this.data.schedule
    if (!schedule || this.data.saving) return
    this.setData({ saving: true })
    wx.showLoading({ title: '正在生成', mask: true })
    try {
      const filePath = await createScheduleImage(this, schedule)
      this.setData({ shareImagePath: filePath })
      await new Promise((resolve, reject) => {
        wx.saveImageToPhotosAlbum({ filePath, success: resolve, fail: reject })
      })
      wx.hideLoading()
      wx.showToast({ title: '已保存到相册', icon: 'success' })
    } catch (error) {
      wx.hideLoading()
      const message = String(error && (error.errMsg || error.message) || error)
      if (!message.includes('cancel')) {
        if (message.includes('auth') || message.includes('deny')) {
          wx.showModal({
            title: '需要相册权限',
            content: this.data.shareImagePath ? '可长按已生成的图片保存，或在设置中允许访问相册' : '请在设置中允许保存图片到相册',
            confirmText: '去设置',
            success: result => {
              if (result.confirm) wx.openSetting()
            },
          })
        } else {
          console.error('[day-detail] 分享图保存失败', error)
          if (this.data.shareImagePath) {
            wx.showModal({ title: '图片已生成', content: '请长按预览图片保存到相册', showCancel: false })
          } else {
            wx.showToast({ title: '图片生成失败，请重试', icon: 'none' })
          }
        }
      }
    } finally {
      this.setData({ saving: false })
    }
  },

  deleteSchedule() {
    const schedule = this.data.schedule
    if (!schedule || this.data.isShared) return
    wx.showModal({
      title: '删除日程',
      content: `确定删除“${schedule.title}”吗？`,
      confirmColor: '#EF4444',
      success: result => {
        if (!result.confirm) return
        try {
          writeSchedules(readSchedules().filter(item => item.id !== schedule.id))
          removePendingSchedule(schedule.id)
          addDeletedId(schedule.id)
          call('days', 'remove', { id: schedule.id }, { silent: true, noRetry: true })
            .then(() => clearDeletedId(schedule.id))
            .catch(() => {})
          wx.showToast({ title: '日程已删除', icon: 'success' })
          setTimeout(() => this.goDays(), 500)
        } catch (error) {
          wx.showToast({ title: '删除失败，请重试', icon: 'none' })
        }
      },
    })
  },

  goDays() {
    const pages = getCurrentPages()
    if (pages.length > 1 && !this.data.isShared) {
      wx.navigateBack({ delta: 1 })
    } else {
      wx.switchTab({ url: '/pages/days/index/index' })
    }
  },

  shareTitle() {
    const schedule = this.data.schedule
    if (!schedule) return '叭啦·日子'
    const timing = this.data.countLabel === '就是今天'
      ? '就是今天'
      : `${this.data.countLabel}${this.data.dayCount}天`
    return `${schedule.title} · ${timing}`
  },

  onShareAppMessage() {
    const schedule = this.data.schedule
    return {
      title: this.shareTitle(),
      path: schedule
        ? `/pages/day-detail/index/index?${buildShareQuery(schedule)}`
        : '/pages/days/index/index',
      imageUrl: this.data.shareImagePath || '/assets/brand/share-card.png',
    }
  },

  onShareTimeline() {
    return {
      title: this.shareTitle(),
      query: this.data.schedule ? buildShareQuery(this.data.schedule) : '',
      imageUrl: this.data.shareImagePath || '/assets/brand/share-card.png',
    }
  },

  onAddToFavorites() {
    return {
      title: this.shareTitle(),
      query: this.data.schedule ? buildShareQuery(this.data.schedule) : '',
      imageUrl: this.data.shareImagePath || '/assets/brand/share-card.png',
    }
  },
}))
