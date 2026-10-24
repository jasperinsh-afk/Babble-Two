/**
 * seedImport —— 演示数据导入云函数（一次性工具，导入完成后可删除）
 *
 * 用途：把 scripts/seed/seed_data.json 的演示数据灌入云数据库。
 * 相比本地 Node 脚本，这里不需要腾讯云 secretId/secretKey，
 * 直接在微信开发者工具「云端测试」触发即可。
 *
 * 云端测试参数：
 *   {}                      导入全部集合（建议先把超时时间调到 60 秒）
 *   { "only": "polls" }     只导入指定集合，避免超时
 *   { "clean": true }       只清空不写入
 */
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

const data = require('./seed_data.json')

const COLLECTIONS = [
  'banners',
  'polls',
  'clubs',
  'club_posts',
  'events',
  'dorm_channels',
  'dorm_posts',
  'lost_found',
  'second_hand',
  'nfc_cards',
  'badges',
]

/**
 * 云函数查询里用到的字段，文档缺失时不会被 where 命中，
 * 这里统一补齐默认值，保证种子数据能被各 action 正确查到。
 */
const DEFAULTS = {
  banners: {},
  polls: { isDeleted: false },
  clubs: { isDeleted: false, memberOpenids: [] },
  club_posts: {},
  events: { isDeleted: false, registeredOpenids: [], waitlistOpenids: [] },
  dorm_channels: { isActive: true },
  dorm_posts: { isDeleted: false, reviewStatus: 'approved' },
  lost_found: { isDeleted: false },
  second_hand: { isDeleted: false },
  nfc_cards: { isActive: true },
  badges: {},
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$/

/** ISO 时间字符串 → Date（云函数里 endAt/startAt 与当前时间比较必须是 Date） */
function toDates(value) {
  if (typeof value === 'string') {
    return ISO_DATE.test(value) ? new Date(value) : value
  }
  if (Array.isArray(value)) return value.map(toDates)
  if (value && typeof value === 'object') {
    Object.keys(value).forEach((k) => {
      value[k] = toDates(value[k])
    })
  }
  return value
}

const DAY = 24 * 60 * 60 * 1000

/**
 * 种子数据里的日期是按编写时间写死的，时间久了会全部过期。
 * 这里对「投票 / 活动」做一次平移：若已过期，整体向后推到今天之后，
 * 保证演示环境里首页今日投票、日历、报名都可用（相对间隔保持不变）。
 */
function ensureActiveWindow(doc) {
  const fields = ['startAt', 'endAt', 'signupDeadline']
  if (!doc.endAt || !(doc.endAt instanceof Date)) return doc

  const now = Date.now()
  if (doc.endAt.getTime() > now) return doc

  const base = doc.startAt instanceof Date ? doc.startAt.getTime() : doc.endAt.getTime()
  // 从「今天 +1 天」开始，保留原本的起止间隔
  const delta = now + DAY - base

  fields.forEach((f) => {
    if (doc[f] instanceof Date) doc[f] = new Date(doc[f].getTime() + delta)
  })
  return doc
}

function normalize(name, items) {
  const defaults = DEFAULTS[name] || {}
  return items.map((raw) => {
    const doc = { ...defaults, ...raw }

    if (name === 'events' && (doc.status === 'published' || doc.status === 'open')) doc.status = 'active'
    if (name === 'dorm_channels') doc.scope = doc.type || 'ALL'
    if (name === 'nfc_cards') {
      // 云函数 loadCard 支持 _id / code 两种查法，checkin 用扁平 target
      doc.code = doc.code || doc.cardId
      if (doc.target) {
        doc.targetType = doc.targetType || doc.target.type || null
        doc.targetId = doc.targetId || doc.target.id || null
      }
    }

    const dated = toDates(doc)
    if (name === 'polls' || name === 'events') return ensureActiveWindow(dated)
    return dated
  })
}

async function clearCollection(name) {
  try {
    let list = await db.collection(name).limit(100).get()
    while (list.data.length) {
      for (const doc of list.data) {
        await db.collection(name).doc(doc._id).remove()
      }
      list = await db.collection(name).limit(100).get()
    }
  } catch (e) {
    // 集合不存在或无权清空时忽略
  }
}

exports.main = async (event = {}) => {
  const { only = '', clean = false } = event || {}
  const result = {}

  for (const coll of COLLECTIONS) {
    if (only && only !== coll) continue

    const items = data[coll] ? normalize(coll, data[coll]) : null
    if (!items) {
      result[coll] = 'no data'
      continue
    }

    await clearCollection(coll)
    if (clean) {
      result[coll] = 'cleared'
      continue
    }

    let ok = 0
    for (const item of items) {
      try {
        await db.collection(coll).add({ data: item })
        ok += 1
      } catch (e) {
        console.error(`[seedImport] ${coll}/${item._id}:`, e.message)
      }
    }
    result[coll] = `${ok}/${items.length}`
  }

  return { ok: true, data: result, message: '导入完成' }
}
