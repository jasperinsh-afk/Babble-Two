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

const CARD_ID_PATTERN = /^[A-Z]{2}-[A-Z]{2}-\d{2}-[A-Z0-9]+$/

function fail(message, code) {
  const err = new Error(message)
  err.code = code
  throw err
}

/** 点位说明（原 NFC 海报点位规则，改为扫码后仍在端上展示） */
const LOCATION_RULES = [
  { type: 'canteen', name: '食堂', desc: '食堂入口海报，扫码参与今日午餐投票' },
  { type: 'library', name: '图书馆', desc: '图书馆一楼公告位，扫码查看读书社团' },
  { type: 'dormitory', name: '宿舍楼', desc: '各楼层电梯口，扫码进入住宿圈' },
  { type: 'bulletin', name: '公告栏', desc: '中央公告栏，扫码查看全校活动' },
  { type: 'classroom', name: '教室区', desc: '教学楼走廊，扫码参与课程相关投票' },
  { type: 'clubroom', name: '社团活动室', desc: '社团活动室门口，扫码直达社团主页' },
  { type: 'sports', name: '体育场馆', desc: '体育馆入口，扫码报名体育赛事' },
  { type: 'gateway', name: '校门', desc: '校门口迎新海报，扫码领取新手勋章' },
]

async function loadCard(key) {
  if (!key) fail('缺少卡片标识')

  let res = await db.collection('nfc_cards').doc(key).get()
  if (!res.data) {
    const byCode = await db
      .collection('nfc_cards')
      .where({ code: key })
      .limit(1)
      .get()
    res = { data: byCode.data[0] || null }
  }
  if (!res.data) fail('点位不存在', 'CARD_NOT_FOUND')
  return res.data
}

/**
 * cardByCode —— 扫码落地：按 cardId 或小程序码 scene 取卡
 * 入参：{ key } —— key 可以是卡编号（QD-CT-01-A01）或小程序码 scene
 */
async function cardByCode(payload = {}) {
  const { key } = payload
  const card = await loadCard(key)

  if (!card.isActive) fail('该点位已停用', 'CARD_INACTIVE')

  const openid = resolveOpenid(payload)
  const [checkinRes, totalRes] = await Promise.all([
    db.collection('nfc_checkins').where({ _openid: openid, cardId: card.cardId }).limit(1).get(),
    db.collection('nfc_checkins').where({ _openid: openid }).count(),
  ])

  return {
    cardId: card.cardId,
    locationDesc: card.locationDesc || '',
    locationType: card.locationType || '',
    targetType: card.targetType,
    targetId: card.targetId || null,
    checked: checkinRes.data.length > 0,
    tapCount: checkinRes.data.length ? checkinRes.data[0].tapCount || 0 : 0,
    uniqueCards: totalRes.total,
    rules: LOCATION_RULES,
  }
}

/** 勋章判定：全量重算（共 6 枚，查询量可控） */
async function evaluateBadges(openid) {
  const [voteCount, scanCount, clubCount, eventCount, defRes, ownedRes] = await Promise.all([
    db.collection('ballots').where({ _openid: openid }).count(),
    db.collection('nfc_checkins').where({ _openid: openid }).count(),
    db.collection('clubs').where({ memberOpenids: openid, isDeleted: false }).count(),
    db.collection('events').where({ registeredOpenids: openid, isDeleted: false }).count(),
    db.collection('badges').get(),
    db.collection('user_badges').where({ _openid: openid }).get(),
  ])

  const counters = {
    vote_count: voteCount.total,
    nfc_unique: scanCount.total,
    club_count: clubCount.total,
    event_count: eventCount.total,
  }

  const owned = new Set(ownedRes.data.map((b) => b.badgeCode))
  const newly = []

  for (const badge of defRes.data) {
    const rule = badge.rule || {}
    if (owned.has(badge.code)) continue
    if ((counters[rule.type] || 0) < (rule.count || 0)) continue
    try {
      await db.collection('user_badges').add({
        data: { _openid: openid, badgeCode: badge.code, earnedAt: new Date() },
      })
    } catch (e) {
      continue
    }
    owned.add(badge.code)
    newly.push({ code: badge.code, name: badge.name, rarity: badge.rarity, iconUrl: badge.iconUrl })
  }

  return { newly, uniqueCards: counters.nfc_unique }
}

/** checkin —— 扫码打卡，同一点位只计一次（tap_count 累加） */
async function checkin(payload = {}) {
  const { key } = payload
  const card = await loadCard(key)
  if (!card.isActive) fail('该点位已停用', 'CARD_INACTIVE')

  const openid = resolveOpenid(payload)
  const now = new Date()

  const res = await db
    .collection('nfc_checkins')
    .where({ _openid: openid, cardId: card.cardId })
    .limit(1)
    .get()

  const existed = res.data[0]
  if (existed) {
    await db
      .collection('nfc_checkins')
      .doc(existed._id)
      .update({ data: { tapCount: _.inc(1), lastTapAt: now } })
  } else {
    await db.collection('nfc_checkins').add({
      data: {
        _openid: openid,
        cardId: card.cardId,
        firstTapAt: now,
        lastTapAt: now,
        tapCount: 1,
      },
    })
  }

  const { newly, uniqueCards } = await evaluateBadges(openid)

  return {
    checked: true,
    firstTime: !existed,
    cardId: card.cardId,
    uniqueCards,
    newBadges: newly,
    target: { type: card.targetType, id: card.targetId || null },
  }
}

const ACTIONS = { cardByCode, checkin }

exports.main = async (event = {}) => {
  const { action = 'cardByCode', payload = {} } = event
  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[scan]', action, err)
    return { ok: false, data: null, message: err.message || '服务异常', code: err.code || '' }
  }
}
