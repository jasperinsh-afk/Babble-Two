const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()

// 网页版身份注入：仅接受 web: 前缀匿名身份，小程序不传时行为不变
function resolveOpenid(payload) {
  const injected = payload && payload.__openid
  if (typeof injected === 'string' && injected.indexOf('web:') === 0) return injected
  return cloud.getWXContext().OPENID
}
const _ = db.command

const PAGE_SIZE = 20

function fail(message) {
  throw new Error(message)
}

function slimEvent(event) {
  return {
    _id: event._id,
    title: event.title,
    description: event.description || '',
    coverUrl: event.coverUrl || '',
    location: event.location || '',
    organizerType: event.organizerType,
    organizerId: event.organizerId || null,
    startAt: event.startAt,
    endAt: event.endAt,
    signupDeadline: event.signupDeadline || null,
    maxParticipants: event.maxParticipants || null,
    status: event.status,
    casType: event.casType || null,
    participantCount: event.participantCount || 0,
  }
}

async function list(payload = {}) {
  const { page = 0 } = payload
  const res = await db
    .collection('events')
    .where({ isDeleted: false, status: _.in(['active', 'full']) })
    .orderBy('startAt', 'asc')
    .skip(page * PAGE_SIZE)
    .limit(PAGE_SIZE)
    .get()

  return { list: res.data.map(slimEvent), hasMore: res.data.length === PAGE_SIZE }
}

/**
 * calendar —— 月视图：返回 [from, to] 区间内的活动 + 每日计数
 * 端上传的月份仅用于确定区间，是否可报名一律以服务端时间判定
 */
async function calendar(payload = {}) {
  const { year, month } = payload // month: 1~12
  const y = Number(year)
  const m = Number(month)
  if (!y || !m) fail('缺少 year 或 month')

  const from = new Date(Date.UTC(y, m - 1, 1, 0, 0, 0))
  const to = new Date(Date.UTC(y, m, 0, 23, 59, 59))

  const res = await db
    .collection('events')
    .where({
      isDeleted: false,
      startAt: _.gte(from).and(_.lte(to)),
    })
    .orderBy('startAt', 'asc')
    .limit(200)
    .get()

  const dayMap = {}
  res.data.forEach((e) => {
    const d = new Date(e.startAt)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
      d.getDate()
    ).padStart(2, '0')}`
    dayMap[key] = (dayMap[key] || 0) + 1
  })

  return {
    days: Object.keys(dayMap).map((date) => ({ date, count: dayMap[date] })),
    events: res.data.map(slimEvent),
  }
}

async function detail(payload = {}) {
  const { eventId } = payload
  if (!eventId) fail('缺少 eventId')

  const openid = resolveOpenid(payload)
  const res = await db.collection('events').doc(eventId).get()
  if (!res.data) fail('活动不存在')

  const e = slimEvent(res.data)
  const registered = res.data.registeredOpenids || []
  const waitlist = res.data.waitlistOpenids || []
  e.registered = registered.indexOf(openid) >= 0
  e.waitlisted = waitlist.indexOf(openid) >= 0
  return e
}

/** 报名：容量满自动进候补队列（E-105） */
async function join(payload = {}) {
  const { eventId } = payload
  if (!eventId) fail('缺少 eventId')

  const openid = resolveOpenid(payload)
  const res = await db.collection('events').doc(eventId).get()
  if (!res.data) fail('活动不存在')

  const e = res.data
  if (e.status === 'cancelled') fail('活动已取消')
  if (e.status === 'closed') fail('报名已结束')
  if (e.signupDeadline && new Date(e.signupDeadline) < new Date()) fail('报名已截止')
  if (e.endAt && new Date(e.endAt) < new Date()) fail('活动已结束')

  const registered = e.registeredOpenids || []
  const waitlist = e.waitlistOpenids || []
  if (registered.indexOf(openid) >= 0) return { joined: true, waitlisted: false, already: true }
  if (waitlist.indexOf(openid) >= 0) return { joined: false, waitlisted: true, already: true }

  const isFull = e.maxParticipants && (e.participantCount || 0) >= e.maxParticipants

  if (isFull) {
    await db
      .collection('events')
      .doc(eventId)
      .update({ data: { waitlistOpenids: _.push([openid]), updatedAt: new Date() } })
    return { joined: false, waitlisted: true, already: false }
  }

  const patch = {
    registeredOpenids: _.push([openid]),
    participantCount: _.inc(1),
    updatedAt: new Date(),
  }
  if (e.maxParticipants && e.participantCount + 1 >= e.maxParticipants) patch.status = 'full'

  await db.collection('events').doc(eventId).update({ data: patch })
  return { joined: true, waitlisted: false, already: false }
}

/** CAS 履历：活动结束且已报名（未签到）也计入，由运营侧注入补充 */
async function myCas(payload = {}) {
  const openid = resolveOpenid(payload)
  const [casRes, eventRes] = await Promise.all([
    db
      .collection('cas_records')
      .where({ _openid: openid })
      .orderBy('happenedAt', 'desc')
      .limit(50)
      .get(),
    db
      .collection('events')
      .where({ registeredOpenids: openid, isDeleted: false })
      .orderBy('startAt', 'desc')
      .limit(50)
      .get(),
  ])

  const byType = { C: 0, A: 0, S: 0 }
  casRes.data.forEach((r) => {
    if (byType[r.casType] !== undefined) byType[r.casType] += 1
  })

  return {
    records: casRes.data.map((r) => ({
      _id: r._id,
      title: r.title,
      casType: r.casType,
      role: r.role || 'participant',
      eventId: r.eventId || null,
      happenedAt: r.happenedAt,
    })),
    stats: byType,
    myEvents: eventRes.data.map(slimEvent),
  }
}

const ACTIONS = { list, calendar, detail, join, myCas }

exports.main = async (event = {}) => {
  const { action = 'list', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[event]', action, err)
    return { ok: false, data: null, message: err.message || '服务异常' }
  }
}
