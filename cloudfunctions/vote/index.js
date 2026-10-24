const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()

// 网页版（bala-web）由服务端经 invokecloudfunction 调用，没有微信客户端上下文，
// 因此网关在 payload.__openid 注入匿名身份。仅接受 web: 前缀，防止伪造他人微信 openid；
// 小程序调用不传该字段，走原有 getWXContext 逻辑，行为完全不变。
function resolveOpenid(payload) {
  const injected = payload && payload.__openid
  if (typeof injected === 'string' && injected.indexOf('web:') === 0) return injected
  return cloud.getWXContext().OPENID
}
const _ = db.command

const POLLS = 'polls'
const BALLOTS = 'ballots'
const BADGES = 'badges'
const USER_BADGES = 'user_badges'

/** 每种题型允许的选项数量区间 */
const OPTION_RANGE = {
  single: [1, 1],
  multi: [1, 8],
  pk: [1, 1],
  ranking: [2, 6],
  groupbuy: [1, 1],
}

function fail(message, code) {
  const err = new Error(message)
  err.code = code
  throw err
}

// ---------------------------------------------------------------- 勋章

/** 采集该用户各项计数器（用于勋章判定） */
async function collectCounters(openid) {
  const [voteCount, scanRes, clubCount, eventCount, streakRes] = await Promise.all([
    db.collection(BALLOTS).where({ _openid: openid }).count(),
    db.collection('nfc_checkins').where({ _openid: openid }).count(),
    db.collection('clubs').where({ memberOpenids: openid, isDeleted: false }).count(),
    db.collection('events').where({ registeredOpenids: openid, isDeleted: false }).count(),
    db
      .collection(BALLOTS)
      .where({ _openid: openid })
      .orderBy('createdAt', 'desc')
      .limit(60)
      .field({ createdAt: true })
      .get(),
  ])

  // 连续投票天数：从今天起往前逐日递减，断天即停
  const daySet = new Set()
  streakRes.data.forEach((b) => {
    const d = new Date(b.createdAt)
    daySet.add(`${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`)
  })
  let streak = 0
  const cursor = new Date()
  for (let i = 0; i < 400; i += 1) {
    const key = `${cursor.getFullYear()}-${cursor.getMonth()}-${cursor.getDate()}`
    if (!daySet.has(key)) break
    streak += 1
    cursor.setDate(cursor.getDate() - 1)
  }

  return {
    vote_count: voteCount.total,
    nfc_unique: scanRes.total,
    club_count: clubCount.total,
    event_count: eventCount.total,
    vote_streak: streak,
  }
}

/** 全量重算勋章并发放（幂等，写 user_badges 唯一索引兜底） */
async function evaluateBadges(openid) {
  const counters = await collectCounters(openid)
  const [defRes, ownedRes] = await Promise.all([
    db.collection(BADGES).get(),
    db.collection(USER_BADGES).where({ _openid: openid }).get(),
  ])

  const owned = new Set(ownedRes.data.map((b) => b.badgeCode))
  const newly = []

  for (const badge of defRes.data) {
    const rule = badge.rule || {}
    if (owned.has(badge.code)) continue
    if ((counters[rule.type] || 0) < (rule.count || 0)) continue

    try {
      await db.collection(USER_BADGES).add({
        data: {
          _openid: openid,
          badgeCode: badge.code,
          earnedAt: new Date(),
        },
      })
    } catch (e) {
      continue // 唯一索引冲突 = 已发放，忽略
    }
    owned.add(badge.code)
    newly.push({ code: badge.code, name: badge.name, rarity: badge.rarity, iconUrl: badge.iconUrl })
  }

  return newly
}

// ---------------------------------------------------------------- 读

function slimPoll(poll) {
  return {
    _id: poll._id,
    title: poll.title,
    description: poll.description || '',
    pollType: poll.pollType,
    status: poll.status,
    tag: poll.tag,
    category: poll.category,
    topicTags: poll.topicTags || [],
    coverUrl: poll.coverUrl || '',
    startAt: poll.startAt || null,
    endAt: poll.endAt || null,
    allowChange: !!poll.allowChange,
    maxChoices: poll.maxChoices || null,
    maxParticipants: poll.maxParticipants || null,
    totalVotes: poll.totalVotes || 0,
    participantCount: poll.participantCount || 0,
    options: (poll.options || []).map((o) => ({
      optionId: o.optionId,
      label: o.label,
      sortOrder: o.sortOrder || 0,
      count: o.count || 0,
    })),
  }
}

const PAGE_SIZE = 20

async function list(payload = {}) {
  const { tag = '', page = 0 } = payload
  const where = { status: 'active', isDeleted: false }
  if (tag && tag !== 'all') where.tag = tag

  const res = await db
    .collection(POLLS)
    .where(where)
    .orderBy('createdAt', 'desc')
    .skip(page * PAGE_SIZE)
    .limit(PAGE_SIZE)
    .get()

  return { list: res.data.map(slimPoll), hasMore: res.data.length === PAGE_SIZE }
}

async function detail(payload = {}) {
  const { pollId } = payload
  if (!pollId) fail('缺少 pollId')

  const openid = resolveOpenid(payload)
  const res = await db.collection(POLLS).doc(pollId).get()
  if (!res.data) fail('投票不存在')

  const poll = slimPoll(res.data)
  const myRes = await db
    .collection(BALLOTS)
    .where({ _openid: openid, pollId })
    .limit(1)
    .get()

  const mine = myRes.data[0] || null
  poll.myChoice = mine ? mine.optionIds || (mine.optionId ? [mine.optionId] : []) : []
  poll.hasVoted = !!mine
  poll.isChanged = mine ? !!mine.isChanged : false
  poll.canChange = poll.allowChange && !(mine && mine.isChanged)

  if (poll.pollType === 'groupbuy') {
    poll.joined = !!mine
    poll.joinedOptionId = mine ? mine.optionId : null
    poll.isFull = poll.maxParticipants ? poll.participantCount >= poll.maxParticipants : false
  }

  return poll
}

async function results(payload = {}) {
  const { pollId } = payload
  if (!pollId) fail('缺少 pollId')

  const res = await db.collection(POLLS).doc(pollId).get()
  if (!res.data) fail('投票不存在')

  const poll = res.data
  const options = (poll.options || []).map((o) => ({
    optionId: o.optionId,
    label: o.label,
    count: o.count || 0,
  }))
  const total = poll.totalVotes || 0

  return {
    pollId,
    total,
    options: options.map((o) => ({
      ...o,
      percent: total ? Math.round((o.count / total) * 1000) / 10 : 0,
    })),
    // 已移除用户资料体系，不再提供年级/住宿楼维度的分组统计
    groups: [],
  }
}

// ---------------------------------------------------------------- 写

/** 载入并校验投票可参与性（时间一律用服务端时间判定） */
async function loadVotablePoll(pollId) {
  const res = await db.collection(POLLS).doc(pollId).get()
  const poll = res.data
  if (!poll || poll.isDeleted) fail('投票不存在')
  if (poll.status === 'draft' || poll.status === 'archived' || poll.status === 'withdrawn') {
    fail('投票未开放')
  }

  const now = new Date()
  if (poll.startAt && new Date(poll.startAt) > now) fail('投票尚未开始')
  if (poll.status === 'closed' || (poll.endAt && new Date(poll.endAt) < now)) fail('投票已结束')

  return poll
}

async function cast(payload = {}) {
  const { pollId, optionIds = [] } = payload
  if (!pollId) fail('缺少 pollId')

  const openid = resolveOpenid(payload)
  const poll = await loadVotablePoll(pollId)

  const range = OPTION_RANGE[poll.pollType] || [1, 1]
  if (optionIds.length < range[0] || optionIds.length > range[1]) {
    fail(`该题需选择 ${range[0]}~${range[1]} 个选项`)
  }
  if (poll.pollType === 'multi' && poll.maxChoices && optionIds.length > poll.maxChoices) {
    fail(`最多可选 ${poll.maxChoices} 项`)
  }

  const validIds = new Set((poll.options || []).map((o) => o.optionId))
  if (optionIds.some((id) => !validIds.has(id))) fail('选项不合法')

  // 接龙满员校验（服务端快照，端上传值不可信）
  if (poll.pollType === 'groupbuy' && poll.maxParticipants) {
    const existing = await db
      .collection(BALLOTS)
      .where({ _openid: openid, pollId })
      .limit(1)
      .get()
    if (!existing.data.length && (poll.participantCount || 0) >= poll.maxParticipants) {
      fail('接龙人数已满')
    }
  }

  const myRes = await db.collection(BALLOTS).where({ _openid: openid, pollId }).limit(1).get()
  const mine = myRes.data[0] || null

  if (mine) {
    if (!poll.allowChange) fail('该投票不支持改票')
    if (mine.isChanged) fail('你已修改过一次')

    // 撤回旧票计数
    const oldIds = mine.optionIds || (mine.optionId ? [mine.optionId] : [])
    const revert = { totalVotes: _.inc(-1) }
    oldIds.forEach((id) => {
      const idx = (poll.options || []).findIndex((o) => o.optionId === id)
      if (idx >= 0) revert[`options.${idx}.count`] = _.inc(-1)
    })
    if (poll.pollType === 'groupbuy') revert.participantCount = _.inc(-1)
    await db.collection(POLLS).doc(pollId).update({ data: revert })
  }

  // 记新票
  const apply = { totalVotes: _.inc(1) }
  optionIds.forEach((id) => {
    const idx = (poll.options || []).findIndex((o) => o.optionId === id)
    if (idx >= 0) apply[`options.${idx}.count`] = _.inc(1)
  })
  if (poll.pollType === 'groupbuy') apply.participantCount = _.inc(1)
  await db.collection(POLLS).doc(pollId).update({ data: apply })

  const now = new Date()
  const record = {
    _openid: openid,
    pollId,
    optionId: optionIds.length === 1 ? optionIds[0] : null,
    optionIds,
    isChanged: !!mine,
    updatedAt: now,
  }

  if (mine) {
    await db.collection(BALLOTS).doc(mine._id).update({ data: record })
  } else {
    await db.collection(BALLOTS).add({ data: { ...record, createdAt: now } })
  }

  const newBadges = await evaluateBadges(openid)
  return { voted: true, changed: !!mine, optionIds, newBadges }
}

async function joinChain(payload = {}) {
  const { pollId, optionId } = payload
  if (!pollId || !optionId) fail('缺少 pollId 或 optionId')

  const poll = await db.collection(POLLS).doc(pollId).get()
  if (!poll.data || poll.data.pollType !== 'groupbuy') fail('接龙不存在')

  return cast({ pollId, optionIds: [optionId] })
}

async function leaveChain(payload = {}) {
  const { pollId } = payload
  if (!pollId) fail('缺少 pollId')

  const openid = resolveOpenid(payload)
  const myRes = await db.collection(BALLOTS).where({ _openid: openid, pollId }).limit(1).get()
  const mine = myRes.data[0]
  if (!mine) fail('你还没有接龙')

  const pollRes = await db.collection(POLLS).doc(pollId).get()
  const poll = pollRes.data
  if (poll && poll.endAt && new Date(poll.endAt) < new Date()) fail('接龙已结束')

  const oldIds = mine.optionIds || (mine.optionId ? [mine.optionId] : [])
  const revert = { totalVotes: _.inc(-1), participantCount: _.inc(-1) }
  oldIds.forEach((id) => {
    const idx = (poll?.options || []).findIndex((o) => o.optionId === id)
    if (idx >= 0) revert[`options.${idx}.count`] = _.inc(-1)
  })
  await db.collection(POLLS).doc(pollId).update({ data: revert })
  await db.collection(BALLOTS).doc(mine._id).remove()

  return { left: true }
}

const ACTIONS = { list, detail, results, cast, joinChain, leaveChain }

exports.main = async (event = {}) => {
  const { action = 'list', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[vote]', action, err)
    return { ok: false, data: null, message: err.message || '服务异常' }
  }
}
