const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()

// 网页版身份注入：仅接受 web: 前缀匿名身份，小程序不传时行为不变
function resolveOpenid(payload) {
  const injected = payload && payload.__openid
  if (typeof injected === 'string' && injected.indexOf('web:') === 0) return injected
  return cloud.getWXContext().OPENID
}

/**
 * me.overview —— 本地足迹（原「我的」，无账号体系）
 *
 * 全部数据按 _openid 聚合：参与投票数、扫码打卡数、已获勋章、近期足迹。
 * 端上仅展示，不提供任何编辑入口。
 */
async function overview(payload = {}) {
  const openid = resolveOpenid(payload)

  const [voteRes, checkinRes, badgeRes, defRes, recentVoteRes] = await Promise.all([
    db.collection('ballots').where({ _openid: openid }).count(),
    db.collection('nfc_checkins').where({ _openid: openid }).count(),
    db.collection('user_badges').where({ _openid: openid }).orderBy('earnedAt', 'desc').get(),
    db.collection('badges').get(),
    db
      .collection('ballots')
      .where({ _openid: openid })
      .orderBy('createdAt', 'desc')
      .limit(20)
      .get(),
  ])

  const pollIds = [...new Set(recentVoteRes.data.map((b) => b.pollId))]
  let pollMap = {}
  if (pollIds.length) {
    const pollRes = await db
      .collection('polls')
      .where({ _id: db.command.in(pollIds) })
      .field({ title: true, pollType: true })
      .get()
    pollMap = pollRes.data.reduce((acc, p) => {
      acc[p._id] = p
      return acc
    }, {})
  }

  const ownedMap = badgeRes.data.reduce((acc, b) => {
    acc[b.badgeCode] = b.earnedAt
    return acc
  }, {})

  const badges = defRes.data.map((b) => ({
    code: b.code,
    name: b.name,
    description: b.description || '',
    iconUrl: b.iconUrl || '',
    rarity: b.rarity,
    rule: b.rule || {},
    earnedAt: ownedMap[b.code] || null,
    unlocked: !!ownedMap[b.code],
  }))

  const recentCheckinRes = await db
    .collection('nfc_checkins')
    .where({ _openid: openid })
    .orderBy('lastTapAt', 'desc')
    .limit(10)
    .get()

  return {
    stats: {
      voteCount: voteRes.total,
      checkinCount: checkinRes.total,
      badgeCount: badgeRes.data.length,
      badgeTotal: defRes.data.length,
    },
    badges,
    recentVotes: recentVoteRes.data.map((b) => ({
      pollId: b.pollId,
      title: pollMap[b.pollId] ? pollMap[b.pollId].title : '（已下架投票）',
      optionIds: b.optionIds || (b.optionId ? [b.optionId] : []),
      createdAt: b.createdAt,
    })),
    recentCheckins: recentCheckinRes.data.map((c) => ({
      cardId: c.cardId,
      tapCount: c.tapCount || 1,
      firstTapAt: c.firstTapAt,
      lastTapAt: c.lastTapAt || c.firstTapAt,
    })),
  }
}

// ---------------------------------------------------------------- 消息中心

const MESSAGE_PAGE = 20

/** 消息偏好默认值（全部开启）；文档缺失的键以此兜底 */
const DEFAULT_PREFS = {
  eventChange: true,
  eventCancel: true,
  pollResult: true,
  ownerResponse: true,
  deadline: true,
}

const PREF_KEYS = Object.keys(DEFAULT_PREFS)

function slimMessage(m) {
  return {
    _id: m._id,
    type: m.type,
    title: m.title,
    content: m.content,
    refType: m.refType || '',
    refId: m.refId || '',
    readAt: m.readAt || null,
    createdAt: m.createdAt,
  }
}

function shapePrefs(doc) {
  const out = { ...DEFAULT_PREFS }
  PREF_KEYS.forEach((k) => {
    if (typeof doc[k] === 'boolean') out[k] = doc[k]
  })
  return out
}

/**
 * me.messages —— 消息中心分页读取
 *
 * cursor 为上一页最后一条的 createdAt（倒序分页，严格小于游标）。
 * unread 为当前用户全部未读数（不受 type/unreadOnly 过滤影响）。
 */
async function messages(payload = {}) {
  const openid = resolveOpenid(payload)
  const where = { _openid: openid }
  if (payload.type) where.type = payload.type
  if (payload.unreadOnly) where.readAt = null

  if (payload.cursor) {
    const cursorDate = new Date(payload.cursor)
    if (!isNaN(cursorDate.getTime())) where.createdAt = db.command.lt(cursorDate)
  }

  const [listRes, unreadRes] = await Promise.all([
    db
      .collection('messages')
      .where(where)
      .orderBy('createdAt', 'desc')
      .limit(MESSAGE_PAGE)
      .get(),
    db.collection('messages').where({ _openid: openid, readAt: null }).count(),
  ])

  return {
    list: listRes.data.map(slimMessage),
    hasMore: listRes.data.length === MESSAGE_PAGE,
    unread: unreadRes.total,
  }
}

/**
 * me.markRead —— 标记已读
 *
 * 三种入参：{ ids: [...] } / { id } / { all: true }。
 * where 必带 _openid，杜绝标记他人消息；readAt: null 保证只统计真正未读的条数。
 */
async function markRead(payload = {}) {
  const openid = resolveOpenid(payload)
  const where = { _openid: openid, readAt: null }

  if (!payload.all) {
    if (payload.ids && payload.ids.length) where._id = db.command.in(payload.ids)
    else if (payload.id) where._id = payload.id
    else fail('缺少要标记的消息')
  }

  const res = await db.collection('messages').where(where).update({ data: { readAt: new Date() } })
  return { updated: (res.stats && res.stats.updated) || 0 }
}

/**
 * me.messagePrefs —— 消息偏好读写
 *
 * 无参或 prefs 为空时返回当前偏好（与默认值合并）；
 * 带 payload.prefs 时按 _openid upsert（存在则更新，不存在则新建）。
 */
async function messagePrefs(payload = {}) {
  const openid = resolveOpenid(payload)
  const incoming = payload.prefs

  if (incoming && typeof incoming === 'object') {
    const patch = { updatedAt: new Date() }
    PREF_KEYS.forEach((k) => {
      if (typeof incoming[k] === 'boolean') patch[k] = incoming[k]
    })
    const existRes = await db.collection('message_prefs').where({ _openid: openid }).limit(1).get()
    if (existRes.data.length) {
      await db.collection('message_prefs').doc(existRes.data[0]._id).update({ data: patch })
    } else {
      await db.collection('message_prefs').add({ data: { _openid: openid, ...patch } })
    }
    return { prefs: shapePrefs({ ...DEFAULT_PREFS, ...patch }) }
  }

  const res = await db.collection('message_prefs').where({ _openid: openid }).limit(1).get()
  return { prefs: shapePrefs(res.data[0] || {}) }
}

const ACTIONS = { overview, messages, markRead, messagePrefs }

exports.main = async (event = {}) => {
  const { action = 'overview', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[me]', action, err)
    return { ok: false, data: null, message: err.message || '服务异常' }
  }
}
