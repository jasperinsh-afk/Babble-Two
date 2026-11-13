const cloud = require('wx-server-sdk')
const {
  POINTS,
  MEDAL_NAME,
  WEEK_MS,
  weekStart,
  weekKey,
  previousWeekStart,
  dayStart,
  sanitizeNickname,
  aggregateRecords,
  rankNumber,
} = require('./score')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })
const db = cloud.database()
const _ = db.command

function resolveOpenid(payload) {
  const injected = payload && payload.__openid
  if (typeof injected === 'string' && injected.indexOf('web:') === 0) return injected
  // 网页端绑定小程序账号后，服务端注入 linked:<openid>，数据归属同一微信账号
  if (typeof injected === 'string' && injected.indexOf('linked:') === 0) return injected.slice(7)
  return cloud.getWXContext().OPENID
}

const AVATARS = ['🦊', '🐼', '🐯', '🐨', '🦁', '🐸', '🐙', '🦄', '🐳', '🌻', '🍀', '⚡']

function displayName(profile, openid) {
  return (profile && profile.nickname) || '校园同学'
}

function avatarFor(openid) {
  let hash = 0
  for (const char of String(openid || '')) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return AVATARS[hash % AVATARS.length]
}

async function profileOf(openid) {
  const res = await db.collection('user_profiles').where({ _openid: openid }).limit(1).get()
  return res.data[0] || null
}

async function profilesOf(openids) {
  if (!openids.length) return {}
  const res = await db.collection('user_profiles').where({ _openid: _.in(openids) }).limit(100).get()
  return res.data.reduce((map, profile) => {
    map[profile._openid] = profile
    return map
  }, {})
}

async function scoringRecords(start) {
  const end = new Date(start.getTime() + WEEK_MS)
  const key = weekKey(start)
  const [ballots, events] = await Promise.all([
    db.collection('ballots').where({ createdAt: _.gte(start), createdAt: _.lt(end) }).limit(1000).get(),
    db.collection('point_events').where({ weekKey: key }).limit(1000).get(),
  ])
  return ballots.data.map(item => ({ _openid: item._openid, points: POINTS.vote, createdAt: item.createdAt }))
    .concat(events.data.map(item => ({
      _openid: item._openid,
      points: item.points,
      createdAt: item.createdAt,
    })))
}

async function awardPoint(openid, { eventKey, points, reason }) {
  const existing = await db.collection('point_events').where({ _openid: openid, eventKey }).limit(1).get()
  if (existing.data.length) return false
  const now = new Date()
  await db.collection('point_events').add({
    data: { _openid: openid, eventKey, points, reason, weekKey: weekKey(now), createdAt: now },
  })
  const profile = await profileOf(openid)
  if (profile) {
    await db.collection('user_profiles').doc(profile._id).update({
      data: { totalPoints: _.inc(points), updatedAt: now },
    })
  } else {
    await db.collection('user_profiles').add({
      data: { _openid: openid, nickname: '', totalPoints: points, createdAt: now, updatedAt: now },
    })
  }
  return true
}

async function track(payload) {
  const openid = resolveOpenid(payload)
  if (payload.type !== 'schedule:create') return { awarded: false, message: '不支持的积分行为' }
  const scheduleId = String(payload.scheduleId || '')
  if (!/^[a-zA-Z0-9-]{6,80}$/.test(scheduleId)) return { awarded: false, message: '日程标识无效' }
  const today = dayStart(new Date())
  const daily = await db.collection('point_events').where({
    _openid: openid,
    reason: '添加日程',
    createdAt: _.gte(today),
  }).count()
  if (daily.total >= 3) return { awarded: false, points: 0, message: '今日添加日程积分已达上限' }
  const awarded = await awardPoint(openid, {
    eventKey: `schedule:${scheduleId}`,
    points: POINTS.schedule,
    reason: '添加日程',
  })
  return { awarded, points: awarded ? POINTS.schedule : 0 }
}

async function setNickname(payload) {
  const openid = resolveOpenid(payload)
  const nickname = sanitizeNickname(payload.nickname)
  if (Array.from(nickname).length < 2) throw new Error('昵称至少需要 2 个字符')
  const now = new Date()
  const profile = await profileOf(openid)
  if (profile) {
    await db.collection('user_profiles').doc(profile._id).update({ data: { nickname, updatedAt: now } })
  } else {
    await db.collection('user_profiles').add({
      data: { _openid: openid, nickname, totalPoints: 0, createdAt: now, updatedAt: now },
    })
  }
  await awardPoint(openid, { eventKey: 'profile:nickname', points: POINTS.nickname, reason: '首次设置昵称' })
  return { nickname }
}

async function settlePreviousWeek() {
  const start = previousWeekStart(new Date())
  const key = weekKey(start)
  const existing = await db.collection('weekly_champions').where({ weekKey: key }).limit(1).get()
  if (existing.data.length) return
  const sorted = aggregateRecords(await scoringRecords(start))
  if (!sorted.length) return
  const winner = sorted[0]
  const profile = await profileOf(winner._openid)
  await db.collection('weekly_champions').doc(key).set({
    data: {
      _openid: winner._openid,
      weekKey: key,
      nickname: displayName(profile, winner._openid),
      points: winner.points,
      medalCode: 'weekly_star',
      medalName: MEDAL_NAME,
      earnedAt: new Date(),
    },
  })
}

async function my(payload) {
  const openid = resolveOpenid(payload)
  const [profile, votes, currentRecords, champions] = await Promise.all([
    profileOf(openid),
    db.collection('ballots').where({ _openid: openid }).count(),
    scoringRecords(weekStart(new Date())),
    db.collection('weekly_champions').where({ _openid: openid }).orderBy('earnedAt', 'desc').limit(20).get(),
  ])
  const current = aggregateRecords(currentRecords).find(item => item._openid === openid)
  return {
    nickname: displayName(profile, openid),
    nicknameSet: Boolean(profile && profile.nickname),
    totalPoints: (profile ? profile.totalPoints || 0 : 0) + votes.total * POINTS.vote,
    currentWeekPoints: current ? current.points : 0,
    champions: champions.data.map(item => ({
      weekKey: item.weekKey,
      points: item.points,
      medalName: item.medalName || MEDAL_NAME,
      earnedAt: item.earnedAt,
    })),
  }
}

async function weekly(payload) {
  const openid = resolveOpenid(payload)
  await settlePreviousWeek()
  const key = weekKey(new Date())
  const sorted = aggregateRecords(await scoringRecords(weekStart(new Date())))
  const profileIds = sorted.slice(0, 50).map(item => item._openid)
  if (!profileIds.includes(openid)) profileIds.push(openid)
  const [profiles, me] = await Promise.all([profilesOf(profileIds), my(payload)])
  const rows = sorted.map((item, index) => ({
    key: `${index}-${item.points}`,
    rank: rankNumber(sorted, index),
    nickname: displayName(profiles[item._openid], item._openid),
    avatar: avatarFor(item._openid),
    points: item.points,
    isMe: item._openid === openid,
    medal: index === 0 ? MEDAL_NAME : '',
  }))
  return {
    weekKey: key,
    list: rows.slice(0, 50),
    my: {
      ...me,
      rank: rows.find(item => item.isMe)?.rank || 0,
      currentWeekPoints: sorted.find(item => item._openid === openid)?.points || 0,
    },
    rules: [
      `参与投票 +${POINTS.vote} 分`,
      `添加日程 +${POINTS.schedule} 分（每日最多 3 次）`,
      `首次设置昵称 +${POINTS.nickname} 分`,
      `每周第一名获得「${MEDAL_NAME}」勋章`,
    ],
  }
}

let collectionsReady = null
function ensureCollections() {
  if (!collectionsReady) {
    collectionsReady = Promise.all(['user_profiles', 'point_events', 'weekly_champions'].map(async name => {
      try {
        await db.createCollection(name)
      } catch (error) {
        if (!String(error.message || error).includes('exist')) throw error
      }
    }))
  }
  return collectionsReady
}

const ACTIONS = { weekly, my, setNickname, track }
exports.main = async (event = {}) => {
  const { action = 'weekly', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }
  try {
    await ensureCollections()
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (error) {
    console.error('[leaderboard]', action, error)
    return { ok: false, data: null, message: error.message || '服务异常' }
  }
}
