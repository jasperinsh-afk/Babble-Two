const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()
const _ = db.command

const LIMIT = {
  banner: 5,
  today: 1,
  hot: 5,
  event: 3,
  club: 6,
  announcement: 3,
  recent: 5,
  calendar: 30,
}

/** 新集合尚未创建时不能让整个首页挂掉 */
async function safeGet(query, label) {
  try {
    const res = await query
    return res && Array.isArray(res.data) ? res.data : []
  } catch (err) {
    console.warn(`[home] ${label} 读取失败，按空列表处理`, err && err.message)
    return []
  }
}

/** 只取端上真正需要的字段，避免把整文档打到端上 */
function slimPoll(poll) {
  return {
    _id: poll._id,
    title: poll.title,
    description: poll.description || '',
    pollType: poll.pollType,
    tag: poll.tag,
    category: poll.category,
    coverUrl: poll.coverUrl || '',
    endAt: poll.endAt || null,
    totalVotes: poll.totalVotes || 0,
    participantCount: poll.participantCount || 0,
    maxParticipants: poll.maxParticipants || null,
    options: (poll.options || []).map((o) => ({
      optionId: o.optionId,
      label: o.label,
    })),
  }
}

function slimEvent(event) {
  return {
    _id: event._id,
    title: event.title,
    location: event.location || '',
    coverUrl: event.coverUrl || '',
    startAt: event.startAt,
    endAt: event.endAt,
    organizerType: event.organizerType,
    status: event.status,
    participantCount: event.participantCount || 0,
    maxParticipants: event.maxParticipants || null,
  }
}

function slimClub(club) {
  return {
    _id: club._id,
    name: club.name,
    description: club.description || '',
    coverUrl: club.coverUrl || '',
    logoUrl: club.logoUrl || '',
    category: club.category,
    isVerified: !!club.isVerified,
    memberCount: club.memberCount || 0,
    heatScore: club.heatScore || 0,
  }
}

/**
 * home.feed —— 发现首页聚合流
 *
 * 一次云调用内并行查 5 个集合，避免端上 5 次串行调用。
 * 每个集合强制 limit，杜绝全表扫描。
 *
 * 入参：{}
 * 出参：{ ok, data: { banners, todayPoll, hotPolls, events, clubs }, message }
 */
async function feed() {
  const now = new Date()

  const [bannerRes, todayRes, hotRes, eventRes, clubRes] = await Promise.all([
    db
      .collection('banners')
      .where({ isActive: true })
      .orderBy('sort', 'asc')
      .limit(LIMIT.banner)
      .get(),
    db
      .collection('polls')
      .where({
        status: 'active',
        isDeleted: false,
        endAt: _.gt(now),
      })
      .orderBy('endAt', 'asc')
      .limit(LIMIT.today)
      .get(),
    db
      .collection('polls')
      .where(
        _.or(
          { status: 'active', isDeleted: false, endAt: _.gt(now) },
          { status: 'active', isDeleted: false, endAt: db.command.exists(false) },
        ),
      )
      .orderBy('totalVotes', 'desc')
      .limit(LIMIT.hot)
      .get(),
    db
      .collection('events')
      .where(
        _.or(
          { status: _.in(['active', 'full']), isDeleted: false, endAt: _.gt(now) },
          { status: _.in(['active', 'full']), isDeleted: false, endAt: db.command.exists(false) },
        ),
      )
      .orderBy('startAt', 'asc')
      .limit(LIMIT.event)
      .get(),
    db
      .collection('clubs')
      .where({ isDeleted: false })
      .orderBy('heatScore', 'desc')
      .limit(LIMIT.club)
      .get(),
  ])

  let sections = []
  try {
    const layoutRes = await db.collection('site_pages').doc('home').get()
    sections = layoutRes.data && Array.isArray(layoutRes.data.sections) ? layoutRes.data.sections : []
  } catch (err) {
    // 首次部署尚无站点配置时，端上使用内置默认布局。
  }

  // 中国时区（UTC+8）今天 00:00，用于「今日安排 / 校历日程」分组
  const chinaNow = new Date(now.getTime() + 8 * 60 * 60 * 1000)
  const todayKey = chinaNow.toISOString().slice(0, 10)
  const dayStart = new Date(`${todayKey}T00:00:00+08:00`)
  const horizon = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)

  // startAt 在云库可能存 Date，也可能存 ISO 字符串，两种谓词各查一次后按 _id 合并
  const [announcementDocs, recentDocs, calendarByDate, calendarByString] = await Promise.all([
    safeGet(
      db.collection('announcements').where({ isActive: true }).orderBy('sort', 'asc').limit(LIMIT.announcement).get(),
      'announcements',
    ),
    safeGet(
      db
        .collection('polls')
        .where({ status: 'active', isDeleted: false, endAt: _.gt(now) })
        .orderBy('createdAt', 'desc')
        .limit(LIMIT.recent)
        .get(),
      'recentPolls',
    ),
    safeGet(
      db.collection('events').where({ startAt: _.gte(dayStart) }).orderBy('startAt', 'asc').limit(LIMIT.calendar).get(),
      'calendarEvents/date',
    ),
    safeGet(
      db.collection('events').where({ startAt: _.gte(todayKey) }).orderBy('startAt', 'asc').limit(LIMIT.calendar).get(),
      'calendarEvents/string',
    ),
  ])

  const seen = new Set()
  const calendarDocs = [...calendarByDate, ...calendarByString].filter((event) => {
    if (!event || !event._id || seen.has(event._id)) return false
    seen.add(event._id)
    return true
  }).sort((a, b) => new Date(a.startAt) - new Date(b.startAt))

  const todayEvents = []
  const upcomingEvents = []
  calendarDocs.forEach((event) => {
    if (event.status === 'cancelled' || event.isDeleted) return
    const start = new Date(event.startAt)
    if (Number.isNaN(start.getTime()) || start > horizon || start < dayStart) return
    const eventDay = new Date(start.getTime() + 8 * 60 * 60 * 1000).toISOString().slice(0, 10)
    if (eventDay === todayKey) {
      if (todayEvents.length < 5) todayEvents.push(slimEvent(event))
    } else if (upcomingEvents.length < 5) {
      upcomingEvents.push(slimEvent(event))
    }
  })

  return {
    sections,
    announcements: announcementDocs.map((a) => ({
      _id: a._id,
      title: a.title || '',
      content: a.content || '',
      level: a.level || 'info',
    })),
    recentPolls: recentDocs.map(slimPoll),
    calendarEvents: { today: todayEvents, upcoming: upcomingEvents },
    banners: bannerRes.data.map((b) => ({
      _id: b._id,
      title: b.title,
      imageUrl: b.imageUrl,
      targetRoute: b.targetRoute || '',
    })),
    todayPoll: todayRes.data.length ? slimPoll(todayRes.data[0]) : null,
    hotPolls: hotRes.data.map(slimPoll),
    events: eventRes.data.map(slimEvent),
    clubs: clubRes.data.map(slimClub),
  }
}

const ACTIONS = { feed }

exports.main = async (event = {}) => {
  const { action = 'feed', payload = {} } = event
  const fn = ACTIONS[action]

  if (!fn) {
    return { ok: false, data: null, message: `未知操作：${action}` }
  }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[home]', action, err)
    return { ok: false, data: null, message: err.message || '服务异常' }
  }
}
