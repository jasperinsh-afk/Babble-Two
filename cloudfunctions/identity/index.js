const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

/**
 * identity —— 静默换取 openid
 *
 * 全站无登录态：不注册、不落库用户表。
 * openid 仅作为匿名标识，用于投票去重、接龙去重、扫码打卡、勋章归属。
 *
 * 入参：{}
 * 出参：{ ok, data: { openid }, message }
 */
exports.main = async () => {
  const wxContext = cloud.getWXContext()
  const openid = wxContext.OPENID

  if (!openid) {
    return { ok: false, data: null, message: '无法获取用户标识' }
  }

  return { ok: true, data: { openid }, message: 'ok' }
}
