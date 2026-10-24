const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()

// 与 vote/index.js 保持一致：仅接受 web: 前缀注入的匿名身份，防止伪造他人微信 openid；
// 小程序调用不传该字段，走 getWXContext，行为完全不变。
function resolveOpenid(payload) {
  const injected = payload && payload.__openid
  if (typeof injected === 'string' && injected.indexOf('web:') === 0) return injected
  return cloud.getWXContext().OPENID
}

function fail(message, code) {
  const err = new Error(message)
  err.code = code
  throw err
}

/**
 * analytics.track —— 埋点上报（只写不读）
 *
 * 文档落 analytics_events：{ _openid, event, props, createdAt, sessionId }。
 * 端上只回 { ok: true }，不回显任何内容。
 */
async function track(payload = {}) {
  const openid = resolveOpenid(payload)
  const event = payload.event
  if (!event) fail('缺少 event')

  await db.collection('analytics_events').add({
    data: {
      _openid: openid,
      event,
      props: payload.props || {},
      createdAt: new Date(),
      sessionId: payload.sessionId || '',
    },
  })
  return { ok: true }
}

const ACTIONS = { track }

exports.main = async (event = {}) => {
  const { action = 'track', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[analytics]', action, err)
    return { ok: false, data: null, message: err.message || '服务异常' }
  }
}
