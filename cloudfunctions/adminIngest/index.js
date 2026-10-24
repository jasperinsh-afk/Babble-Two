const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV })

const db = cloud.database()
const _ = db.command

/**
 * adminIngest —— 运营侧写入网关
 *
 * 墨麟书院输入层（Python 爬虫 + LLM）与运营后台无法直接连接云开发数据库，
 * 统一经本云函数写入。鉴权用环境变量 INGEST_TOKEN，**绝不**下发到小程序端。
 *
 * 入参：{ token, action, payload }
 * 出参：{ ok, data, message }
 */

/** 允许运营侧批量写入的集合白名单，防止被滥用写入任意集合 */
const WRITABLE = [
  'poll_drafts',
  'polls',
  'banners',
  'nfc_cards',
  'club_posts',
  'dorm_posts',
  'lost_found',
  'second_hand',
  'badges',
  'cas_records',
]

function assertToken(token) {
  const expected = process.env.INGEST_TOKEN
  if (!expected) throw new Error('云函数未配置 INGEST_TOKEN')
  if (!token || token !== expected) throw new Error('TOKEN_INVALID')
}

function now() {
  return new Date()
}

/** 批量写入（存在则更新，不存在则新增），按 _id 幂等 */
async function write(payload = {}) {
  const { collection, items = [] } = payload
  if (WRITABLE.indexOf(collection) < 0) throw new Error(`集合不可写：${collection}`)
  if (!items.length) return { inserted: 0, updated: 0 }

  let inserted = 0
  let updated = 0

  for (const raw of items) {
    const { _id, ...rest } = raw
    const doc = { ...rest, updatedAt: now() }

    if (_id) {
      const exist = await db.collection(collection).doc(_id).get().catch(() => ({ data: null }))
      if (exist.data) {
        await db.collection(collection).doc(_id).update({ data: doc })
        updated += 1
        continue
      }
      await db.collection(collection).doc(_id).set({ data: { ...doc, createdAt: doc.createdAt || now() } })
      inserted += 1
      continue
    }

    await db.collection(collection).add({ data: { ...doc, createdAt: doc.createdAt || now() } })
    inserted += 1
  }

  return { inserted, updated }
}

/** 爬虫草稿入库（ML-I-005）：24h 内同指纹不重复写入 */
async function upsertDraft(payload = {}) {
  const { draft = {} } = payload
  if (!draft.title) throw new Error('草稿缺少 title')

  const fingerprint = draft.fingerprint || null
  if (fingerprint) {
    const dup = await db
      .collection('poll_drafts')
      .where({ fingerprint })
      .limit(1)
      .get()
    if (dup.data.length) return { draftId: dup.data[0]._id, duplicated: true }
  }

  const doc = {
    title: draft.title,
    description: draft.description || '',
    options: draft.options || [],
    pollType: draft.pollType || 'single',
    category: draft.category || 'campus',
    tag: draft.tag || 'campus',
    topicTags: draft.topicTags || [],
    source: draft.source || 'manual',
    sourceUrl: draft.sourceUrl || '',
    summary: draft.summary || '',
    heatScore: draft.heatScore || 0,
    riskLevel: draft.riskLevel || 'none',
    llmSuggestion: draft.llmSuggestion || '',
    fingerprint,
    status: 'pending',
    createdAt: now(),
    updatedAt: now(),
  }

  const res = await db.collection('poll_drafts').add({ data: doc })
  return { draftId: res._id, duplicated: false }
}

/**
 * 草稿发布为正式投票（ML-I-007）
 * 合规红线：必须 status=approved 才允许发布，禁止全自动上线
 */
async function publishPoll(payload = {}) {
  const { draftId, overrides = {} } = payload
  if (!draftId) throw new Error('缺少 draftId')

  const res = await db.collection('poll_drafts').doc(draftId).get()
  const draft = res.data
  if (!draft) throw new Error('草稿不存在')
  if (draft.status !== 'approved') throw new Error('草稿未通过人工审核，禁止发布')

  const options = (overrides.options || draft.options || []).map((o, i) => ({
    optionId: o.optionId || `o${i + 1}`,
    label: o.label,
    sortOrder: i,
    count: 0,
  }))
  if (options.length < 2) throw new Error('至少 2 个选项')

  const startAt = overrides.startAt ? new Date(overrides.startAt) : now()
  const endAt = overrides.endAt
    ? new Date(overrides.endAt)
    : new Date(startAt.getTime() + 24 * 3600 * 1000)

  const pollId = overrides.pollId || `p${Date.now()}`
  await db.collection('polls').doc(pollId).set({
    data: {
      title: overrides.title || draft.title,
      description: overrides.description || draft.description || '',
      pollType: overrides.pollType || draft.pollType || 'single',
      status: 'active',
      category: overrides.category || draft.category || 'campus',
      tag: overrides.tag || draft.tag || 'campus',
      topicTags: overrides.topicTags || draft.topicTags || [],
      startAt,
      endAt,
      allowChange: overrides.allowChange === undefined ? true : !!overrides.allowChange,
      anonymous: true,
      maxChoices: overrides.maxChoices || null,
      maxParticipants: overrides.maxParticipants || null,
      coverUrl: overrides.coverUrl || '',
      sourceType: draft.source ? 'crawler' : 'manual',
      reviewStatus: 'approved',
      options,
      totalVotes: 0,
      participantCount: 0,
      isDeleted: false,
      createdAt: now(),
      updatedAt: now(),
    },
  })

  await db
    .collection('poll_drafts')
    .doc(draftId)
    .update({ data: { status: 'used', publishedPollId: pollId, updatedAt: now() } })

  return { pollId }
}

async function ping() {
  return { pong: true, at: now() }
}

const ACTIONS = { write, upsertDraft, publishPoll, ping }

exports.main = async (event = {}) => {
  const { token, action = 'ping', payload = {} } = event

  try {
    assertToken(token)
  } catch (err) {
    return { ok: false, data: null, message: '鉴权失败' }
  }

  const fn = ACTIONS[action]
  if (!fn) return { ok: false, data: null, message: `未知操作：${action}` }

  try {
    const data = await fn(payload)
    return { ok: true, data, message: 'ok' }
  } catch (err) {
    console.error('[adminIngest]', action, err)
    return { ok: false, data: null, message: err.message || '写入失败' }
  }
}
