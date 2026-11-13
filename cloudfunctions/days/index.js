const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()

function resolveOpenid(payload) {
  const injected = payload && payload.__openid
  if (typeof injected === 'string' && injected.indexOf('web:') === 0) return injected
  // 网页端绑定小程序账号后，服务端注入 linked:<openid>，数据归属同一微信账号
  if (typeof injected === 'string' && injected.indexOf('linked:') === 0) return injected.slice(7)
  return cloud.getWXContext().OPENID
}

function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const date = new Date(`${value}T12:00:00Z`)
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
}

function shape(doc) {
  return {
    id: doc._id,
    title: String(doc.title || '').slice(0, 40),
    date: doc.date || '',
    note: String(doc.note || '').slice(0, 120),
    createdAt: typeof doc.createdAt === 'number' ? doc.createdAt : 0,
  }
}

async function list(payload) {
  const openid = resolveOpenid(payload)
  const res = await db.collection('days').where({ _openid: openid }).limit(100).get()
  const items = res.data.map(shape).sort((a, b) =>
    a.date.localeCompare(b.date) || a.createdAt - b.createdAt,
  )
  return { list: items }
}

async function save(payload) {
  const openid = resolveOpenid(payload)
  const title = String(payload.title || '').trim().slice(0, 40)
  const date = String(payload.date || '').trim()
  const note = String(payload.note || '').trim().slice(0, 120)
  if (!title) throw new Error('请填写日程名称')
  if (!validDate(date)) throw new Error('日期格式不正确')

  const id = String(payload.id || '').slice(0, 80)
  const now = new Date()
  if (id) {
    const existing = await db.collection('days').doc(id).get().catch(() => null)
    // id 冲突时禁止改写他人日程
    if (existing && existing.data && existing.data._openid !== openid) {
      throw new Error('无权修改该日程')
    }
    // 端上 id 即云端 _id，保证新增 / 修改 / 删除 / 跨设备合并都指向同一条记录
    const createdAt = typeof payload.createdAt === 'number'
      ? payload.createdAt
      : (existing && existing.data && typeof existing.data.createdAt === 'number'
        ? existing.data.createdAt
        : Date.now())
    await db.collection('days').doc(id).set({
      data: { _openid: openid, title, date, note, createdAt, updatedAt: now },
    })
    return { schedule: { id, title, date, note, createdAt } }
  }
  const createdAt = Date.now()
  const res = await db.collection('days').add({
    data: { _openid: openid, title, date, note, createdAt, updatedAt: now },
  })
  return { schedule: { id: res._id, title, date, note, createdAt } }
}

async function remove(payload) {
  const openid = resolveOpenid(payload)
  const id = String(payload.id || '')
  if (!id) return { removed: false }
  const existing = await db.collection('days').doc(id).get().catch(() => null)
  if (!existing || !existing.data || existing.data._openid !== openid) return { removed: false }
  await db.collection('days').doc(id).remove()
  return { removed: true }
}

function normalizeWeekdays(value) {
  const values = Array.isArray(value) ? value : String(value || '').split(',')
  const weekdays = [...new Set(values
    .filter(item => String(item).trim() !== '')
    .map(item => Number(item))
    .filter(item => Number.isInteger(item) && item >= 0 && item <= 6),
  )].sort((a, b) => a - b)
  return weekdays.length ? weekdays : [1, 2, 3, 4, 5]
}

async function remote() {
  const [events, countdowns] = await Promise.all([
    db.collection('events').limit(100).get().catch(() => ({ data: [] })),
    db.collection('remote_countdowns').limit(100).get().catch(() => ({ data: [] })),
  ])
  const now = Date.now()
  return {
    events: events.data
      .filter(event => !event.isDeleted && event.status !== 'cancelled')
      .filter(event => {
        const start = new Date(event.startAt).getTime()
        return Number.isFinite(start) && start >= now - 86400000
      })
      .map(event => ({
        _id: event._id,
        title: String(event.title || '').slice(0, 40),
        startAt: event.startAt,
        location: String(event.location || '').slice(0, 60),
        description: String(event.description || '').slice(0, 120),
        status: event.status || '',
      })),
    countdowns: countdowns.data.filter(item => item.isActive !== false).map(item => ({
      _id: item._id,
      code: item.code || '',
      title: String(item.title || '').slice(0, 40),
      description: String(item.description || '').slice(0, 120),
      emoji: item.emoji || '⏰',
      badge: item.badge || '倒计时',
      targetAt: item.targetAt || null,
      dailyTime: item.dailyTime || '',
      weekdays: normalizeWeekdays(item.weekdays),
      isActive: true,
    })),
  }
}

let collectionReady = null
function ensureCollection() {
  if (!collectionReady) {
    collectionReady = Promise.all(['days', 'remote_countdowns'].map(name => (
      db.createCollection(name).catch((error) => {
        if (!String(error.message || error).includes('exist')) throw error
      })
    )))
  }
  return collectionReady
}

const ACTIONS = { list, save, remove, remote }
exports.main = async (event = {}) => {
  const { action = 'list', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }
  try {
    await ensureCollection()
    return { ok: true, data: await fn(payload), message: 'ok' }
  } catch (error) {
    console.error('[days]', action, error)
    return { ok: false, data: null, message: error.message || '服务异常' }
  }
}
