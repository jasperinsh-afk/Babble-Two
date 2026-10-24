/**
 * 本地足迹缓存（替代 Flutter 的 LocalCache / SharedPreferences）
 *
 * 弱网或云调用失败时先用本地数据渲染，联网后以云函数返回为准。
 */

const KEYS = {
  footprints: 'goqd_footprints',
  recentScans: 'goqd_recent_scans',
  homeFeed: 'goqd_home_feed',
}

const MAX_FOOTPRINT = 30

function read(key, fallback) {
  try {
    const raw = wx.getStorageSync(key)
    if (!raw) return fallback
    return typeof raw === 'string' ? JSON.parse(raw) : raw
  } catch (e) {
    return fallback
  }
}

function write(key, value) {
  try {
    wx.setStorageSync(key, JSON.stringify(value))
  } catch (e) {
    /* 忽略存储失败 */
  }
}

/** 记录一次投票足迹（本地缓存，用于「我的」离线展示） */
function pushFootprint(item) {
  const list = read(KEYS.footprints, [])
  const next = [item, ...list.filter((i) => i.pollId !== item.pollId)].slice(0, MAX_FOOTPRINT)
  write(KEYS.footprints, next)
  return next
}

/** 记录一次扫码打卡足迹 */
function pushScan(item) {
  const list = read(KEYS.recentScans, [])
  const next = [item, ...list.filter((i) => i.cardId !== item.cardId)].slice(0, MAX_FOOTPRINT)
  write(KEYS.recentScans, next)
  return next
}

function cacheHomeFeed(data) {
  write(KEYS.homeFeed, { data, at: Date.now() })
}

function getHomeFeed(maxAge = 10 * 60 * 1000) {
  const cached = read(KEYS.homeFeed, null)
  if (!cached || Date.now() - cached.at > maxAge) return null
  return cached.data
}

module.exports = {
  KEYS,
  read,
  write,
  pushFootprint,
  pushScan,
  cacheHomeFeed,
  getHomeFeed,
}
