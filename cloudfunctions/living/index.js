const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()

const PAGE_SIZE = 20

function fail(message) {
  throw new Error(message)
}

/** channels —— 宿舍 / 楼层 / 全校三级频道（L-001~003） */
async function channels() {
  const res = await db
    .collection('dorm_channels')
    .where({ isActive: true })
    .orderBy('scope', 'asc')
    .limit(50)
    .get()

  return {
    list: res.data.map((c) => ({
      _id: c._id,
      name: c.name,
      scope: c.scope,
      building: c.building || '',
      floor: c.floor || '',
      room: c.room || '',
    })),
  }
}

async function channelPosts(payload = {}) {
  const { channelId, page = 0 } = payload
  if (!channelId) fail('缺少 channelId')

  const res = await db
    .collection('dorm_posts')
    .where({ channelId, isDeleted: false, reviewStatus: 'approved' })
    .orderBy('createdAt', 'desc')
    .skip(page * PAGE_SIZE)
    .limit(PAGE_SIZE)
    .get()

  return {
    list: res.data.map((p) => ({
      _id: p._id,
      channelId: p.channelId,
      content: p.content || '',
      images: p.images || [],
      likeCount: p.likeCount || 0,
      createdAt: p.createdAt,
    })),
    hasMore: res.data.length === PAGE_SIZE,
  }
}

async function lostFound(payload = {}) {
  const { kind = '', page = 0 } = payload
  const where = { isDeleted: false }
  if (kind && kind !== 'all') where.kind = kind

  const res = await db
    .collection('lost_found')
    .where(where)
    .orderBy('createdAt', 'desc')
    .skip(page * PAGE_SIZE)
    .limit(PAGE_SIZE)
    .get()

  return {
    list: res.data.map((i) => ({
      _id: i._id,
      kind: i.kind,
      title: i.title,
      description: i.description || '',
      location: i.location || '',
      contact: i.contact || '',
      images: i.images || [],
      isResolved: !!i.isResolved,
      createdAt: i.createdAt,
    })),
    hasMore: res.data.length === PAGE_SIZE,
  }
}

async function secondHand(payload = {}) {
  const { page = 0 } = payload
  const res = await db
    .collection('second_hand')
    .where({ isDeleted: false })
    .orderBy('createdAt', 'desc')
    .skip(page * PAGE_SIZE)
    .limit(PAGE_SIZE)
    .get()

  return {
    // price 单位：分，端上 /100 展示；null 表示面议
    list: res.data.map((i) => ({
      _id: i._id,
      title: i.title,
      description: i.description || '',
      price: i.price === undefined ? null : i.price,
      images: i.images || [],
      contact: i.contact || '',
      isSold: !!i.isSold,
      createdAt: i.createdAt,
    })),
    hasMore: res.data.length === PAGE_SIZE,
  }
}

const ACTIONS = { channels, channelPosts, lostFound, secondHand }

exports.main = async (event = {}) => {
  const { action = 'channels', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[living]', action, err)
    return { ok: false, data: null, message: err.message || '服务异常' }
  }
}
