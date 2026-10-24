// 品牌启动页 · 叭啦 Babble
//
// 冷启动时展示品牌定妆：标志 + 叭啦 Babble（口号随次级组合资产以小字出现，
// 启动页是品牌规范中口号唯一合法的界面出现位），随后进入首页。
// 展示约 1.8s，期间点击任意处可立即跳过。

const SPLASH_MS = 1800

Page({
  data: {},

  onLoad() {
    this._entered = false
    this._timer = setTimeout(() => this.enter(), SPLASH_MS)
  },

  onUnload() {
    if (this._timer) clearTimeout(this._timer)
  },

  enter() {
    if (this._entered) return
    this._entered = true
    if (this._timer) {
      clearTimeout(this._timer)
      this._timer = null
    }
    wx.reLaunch({ url: '/pages/index/index' }).catch(() => {
      wx.switchTab({ url: '/pages/index/index' })
    })
  },

  onTap() {
    this.enter()
  },
})
