const { call } = require('./api')

const OPENID_KEY = 'goqd_openid'

/**
 * 静默身份：wx.login 换 openid，全程无感知、无注册页、无登录页。
 * openid 仅用于投票去重 / 接龙去重 / 扫码打卡 / 勋章归属。
 */
let cached = ''

function local() {
  if (cached) return cached
  try {
    cached = wx.getStorageSync(OPENID_KEY) || ''
  } catch (e) {
    cached = ''
  }
  return cached
}

/** 优先返回本地缓存，异步向云函数换取权威值 */
async function ensureOpenid() {
  if (local()) return cached

  try {
    const data = await call('identity', 'get', {}, { silent: true, noRetry: true })
    if (data && data.openid) {
      cached = data.openid
      try {
        wx.setStorageSync(OPENID_KEY, cached)
      } catch (e) {
        /* 存储失败不影响主流程 */
      }
    }
  } catch (e) {
    /* 换失败时保持匿名，云函数仍可从上下文取到 openid */
  }
  return cached
}

module.exports = { ensureOpenid, local }
