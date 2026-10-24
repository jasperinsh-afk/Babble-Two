/**
 * 云数据库种子脚本
 *
 * 用法：
 *   cd bala-miniapp
 *   node scripts/seed/seed.js <envId>
 *
 * envId 是微信云开发环境 ID，留空则使用默认环境。
 * 该脚本会清空下列集合并重新灌入演示数据，请谨慎在生产环境运行。
 */

const fs = require('fs')
const path = require('path')
const tcb = require('@cloudbase/node-sdk')

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
 * 云函数查询里用到的字段在文档缺失时不会命中，
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
 * 对「投票 / 活动」做一次平移：若已过期，整体向后推到今天之后，
 * 保证演示环境里首页今日投票、日历、报名都可用（相对间隔保持不变）。
 */
function ensureActiveWindow(doc) {
  const fields = ['startAt', 'endAt', 'signupDeadline']
  if (!doc.endAt || !(doc.endAt instanceof Date)) return doc

  const now = Date.now()
  if (doc.endAt.getTime() > now) return doc

  const base = doc.startAt instanceof Date ? doc.startAt.getTime() : doc.endAt.getTime()
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

function loadData() {
  const file = path.join(__dirname, 'seed_data.json')
  return JSON.parse(fs.readFileSync(file, 'utf-8'))
}

async function seed(envId) {
  if (!envId) {
    console.error('请提供云开发环境 ID：node scripts/seed/seed.js <envId>')
    process.exit(1)
  }

  const app = tcb.init({ env: envId })
  const db = app.database()

  const data = loadData()

  for (const coll of COLLECTIONS) {
    const items = data[coll] ? normalize(coll, data[coll]) : null
    if (!items) {
      console.log(`[skip] ${coll}: no data`)
      continue
    }

    console.log(`[seed] ${coll}: ${items.length} items`)
    const collection = db.collection(coll)

    // 清空（服务端 SDK 有权限）
    try {
      const list = await collection.get()
      for (const doc of list.data) {
        await collection.doc(doc._id).remove()
      }
    } catch (e) {
      console.log(`[warn] ${coll} clear failed`, e.message)
    }

    // 批量插入
    for (const item of items) {
      try {
        await collection.add(item)
      } catch (e) {
        console.error(`[error] ${coll}/${item._id}:`, e.message)
      }
    }
  }

  console.log('[done] 种子数据已写入云开发数据库')
}

const envId = process.argv[2]
seed(envId).catch((err) => {
  console.error(err)
  process.exit(1)
})
