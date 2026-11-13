const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

const BIND_CODES = 'bind_codes'
const IDENTITY_LINKS = 'identity_links'
const CODE_TTL = 10 * 60 * 1000

let collectionReady = null
function ensureCollection() {
  if (!collectionReady) {
    collectionReady = Promise.all([BIND_CODES, IDENTITY_LINKS].map(name => (
      db.createCollection(name).catch(error => {
        if (!String(error.message || error).includes('exist')) throw error
      })
    )))
  }
  return collectionReady
}

function fail(message, code) {
  const err = new Error(message)
  err.code = code
  throw err
}

/**
 * identity.get —— 静默换取 openid
 *
 * 全站无登录态：不注册、不落库用户表。
 * openid 仅作为匿名标识，用于投票去重、接龙去重、扫码打卡、勋章归属。
 *
 * 入参：{}
 * 出参：{ openid }
 */
async function get() {
  const openid = cloud.getWXContext().OPENID
  if (!openid) fail('无法获取用户标识')
  return { openid }
}

/**
 * identity.issueBindCode —— 小程序端签发一次性绑定码
 *
 * 用户在小程序「我的 → 绑定网页端」获取 6 位码，再到网页端输入即可完成绑定。
 * 只有微信客户端上下文才能拿到真实 openid，网页端无法伪造，因此绑定可信。
 *
 * 出参：{ code, expiresIn }
 */
async function issueBindCode() {
  const openid = cloud.getWXContext().OPENID
  if (!openid) fail('请在微信内打开小程序')
  await ensureCollection()

  const now = Date.now()
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const code = String(Math.floor(100000 + Math.random() * 900000))
    const existing = await db.collection(BIND_CODES).doc(code).get().catch(() => null)
    // 码已被占用且仍有效：换一个，避免顶掉别人刚生成的码
    if (existing && existing.data && !existing.data.used && Number(existing.data.expiresAt) > now) {
      continue
    }
    await db.collection(BIND_CODES).doc(code).set({
      data: { openid, createdAt: now, expiresAt: now + CODE_TTL, used: false },
    })
    return { code, expiresIn: Math.floor(CODE_TTL / 1000) }
  }
  fail('绑定码生成失败，请重试')
}

const ACTIONS = { get, issueBindCode }

exports.main = async (event = {}) => {
  const { action = 'get', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    return { ok: true, data: await fn(payload), message: 'ok' }
  } catch (error) {
    console.error('[identity]', action, error)
    return { ok: false, data: null, message: error.message || '服务异常', code: error.code || '' }
  }
}
