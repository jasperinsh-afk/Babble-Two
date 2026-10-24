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

const ACTIONS = { overview }

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
