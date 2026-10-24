const { cloudEnv } = require('./utils/config')
const { ensureOpenid } = require('./utils/identity')

App({
  globalData: {
    openid: '',
    // 扫码 / 小程序码冷启动参数，供 pages/scan 消费
    launchOptions: null,
  },

  onLaunch(options) {
    if (wx.cloud) {
      wx.cloud.init({
        env: cloudEnv || undefined,
        traceUser: true,
      })
    } else {
      console.error('当前基础库不支持微信云开发，请升级开发者工具与基础库')
    }

    this.globalData.launchOptions = options

    // 静默换取 openid：无登录页、无授权弹窗，用户全程无感知
    ensureOpenid().then((openid) => {
      this.globalData.openid = openid || ''
    })
  },

  onError(err) {
    console.error('[Babble] 未捕获异常', err)
  },
})
