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

function slimClub(club) {
  return {
    _id: club._id,
    name: club.name,
    description: club.description || '',
    logoUrl: club.logoUrl || '',
    coverUrl: club.coverUrl || '',
    category: club.category,
    isVerified: !!club.isVerified,
    memberCount: club.memberCount || 0,
    followerCount: club.followerCount || 0,
    heatScore: club.heatScore || 0,
  }
}

async function list(payload = {}) {
  const { category = '', keyword = '', page = 0 } = payload
  const where = { isDeleted: false }
  if (category && category !== 'all') where.category = category
  if (keyword) where.name = db.RegExp({ regexp: keyword, options: 'i' })

  const res = await db
    .collection('clubs')
    .where(where)
    .orderBy('heatScore', 'desc')
    .skip(page * PAGE_SIZE)
    .limit(PAGE_SIZE)
    .get()

  return { list: res.data.map(slimClub), hasMore: res.data.length === PAGE_SIZE }
}

async function rank() {
  const res = await db
    .collection('clubs')
    .where({ isDeleted: false })
    .orderBy('heatScore', 'desc')
    .limit(10)
    .get()
  return { list: res.data.map(slimClub) }
}

async function detail(payload = {}) {
  const { clubId } = payload
  if (!clubId) fail('缺少 clubId')

  const openid = resolveOpenid(payload)
  const res = await db.collection('clubs').doc(clubId).get()
  if (!res.data) fail('社团不存在')

  const club = slimClub(res.data)
  // 原实现读的是裁剪后的 club.memberOpenids（已被 slimClub 移除），导致 joined 恒为 false
  club.joined = (res.data.memberOpenids || []).indexOf(openid) >= 0
  club.memberOpenids = undefined
  return club
}

async function posts(payload = {}) {
  const { clubId, page = 0 } = payload
  if (!clubId) fail('缺少 clubId')

  const res = await db
    .collection('club_posts')
    .where({ clubId })
    .orderBy('isPinned', 'desc')
    .orderBy('publishedAt', 'desc')
    .skip(page * PAGE_SIZE)
    .limit(PAGE_SIZE)
    .get()

  return {
    list: res.data.map((p) => ({
      _id: p._id,
      clubId: p.clubId,
      title: p.title || '',
      content: p.content || '',
      images: p.images || [],
      isPinned: !!p.isPinned,
      likeCount: p.likeCount || 0,
      publishedAt: p.publishedAt || null,
    })),
    hasMore: res.data.length === PAGE_SIZE,
  }
}

async function join(payload = {}) {
  const { clubId } = payload
  if (!clubId) fail('缺少 clubId')

  const openid = resolveOpenid(payload)
  const res = await db.collection('clubs').doc(clubId).get()
  if (!res.data) fail('社团不存在')

  const members = res.data.memberOpenids || []
  if (members.indexOf(openid) >= 0) return { joined: true, already: true }

  await db
    .collection('clubs')
    .doc(clubId)
    .update({
      data: {
        memberOpenids: _.push([openid]),
        memberCount: _.inc(1),
        updatedAt: new Date(),
      },
    })

  return { joined: true, already: false }
}

async function leave(payload = {}) {
  const { clubId } = payload
  if (!clubId) fail('缺少 clubId')

  const openid = resolveOpenid(payload)
  const res = await db.collection('clubs').doc(clubId).get()
  if (!res.data) fail('社团不存在')

  const members = res.data.memberOpenids || []
  if (members.indexOf(openid) < 0) return { left: true, already: true }

  await db
    .collection('clubs')
    .doc(clubId)
    .update({
      data: {
        memberOpenids: _.pull(openid),
        memberCount: _.inc(-1),
        updatedAt: new Date(),
      },
    })

  return { left: true, already: false }
}

const ACTIONS = { list, rank, detail, posts, join, leave }

exports.main = async (event = {}) => {
  const { action = 'list', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[club]', action, err)
    return { ok: false, data: null, message: err.message || '服务异常' }
  }
}
