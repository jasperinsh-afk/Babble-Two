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

  return {
    sections,
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
