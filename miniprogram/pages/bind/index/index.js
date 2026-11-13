const { call } = require('../../../utils/api')

Page({
  data: {
    codeText: '------',
    rawCode: '',
    secondsLeft: 0,
    expired: false,
    loading: false,
    error: '',
    expireText: '正在生成绑定码…',
  },

  _timer: null,

  onLoad() {
    this.issueCode()
  },

  onUnload() {
    this.clearTimer()
  },

  onHide() {
    this.clearTimer()
  },

  onShow() {
    if (this.data.rawCode && this.data.secondsLeft > 0 && !this._timer) {
      this._timer = setInterval(() => this.tick(), 1000)
    }
  },

  clearTimer() {
    if (this._timer) clearInterval(this._timer)
    this._timer = null
  },

  async issueCode() {
    if (this.data.loading) return
    this.clearTimer()
    this.setData({ loading: true, error: '', expired: false, expireText: '正在生成绑定码…' })
    try {
      const data = await call('identity', 'issueBindCode', {}, { silent: true })
      const seconds = Number(data.expiresIn) || 600
      this.setData({
        rawCode: String(data.code || ''),
        codeText: String(data.code || '').split('').join(' '),
        secondsLeft: seconds,
        expireText: `${Math.floor(seconds / 60)} 分钟后过期`,
      })
      this.clearTimer()
      this._timer = setInterval(() => this.tick(), 1000)
    } catch (error) {
      console.error('[bind] 生成绑定码失败', error)
      this.setData({
        codeText: '------',
        rawCode: '',
        error: '生成失败，请确认 identity 云函数已部署后重试',
        expireText: '',
      })
    } finally {
      this.setData({ loading: false })
    }
  },

  tick() {
    const left = this.data.secondsLeft - 1
    if (left <= 0) {
      this.clearTimer()
      this.setData({ secondsLeft: 0, expired: true, expireText: '绑定码已过期，请重新生成' })
      return
    }
    const mm = Math.floor(left / 60)
    const ss = String(left % 60).padStart(2, '0')
    this.setData({ secondsLeft: left, expireText: `${mm}:${ss} 后过期` })
  },

  copyCode() {
    if (!this.data.rawCode || this.data.expired) {
      wx.showToast({ title: '请先生成有效绑定码', icon: 'none' })
      return
    }
    wx.setClipboardData({ data: this.data.rawCode })
  },
})
