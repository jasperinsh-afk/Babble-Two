/**
 * 微信内分享场景统一封装
 *
 * 覆盖的场景：
 *  - 分享给朋友 / 群聊（右上角菜单、<button open-type="share">）：onShareAppMessage
 *  - 分享到朋友圈（单页模式）：onShareTimeline
 *  - 长按 / 菜单「收藏」：onAddToFavorites
 *  - 右上角菜单里同时放出「发送给朋友」「分享到朋友圈」：wx.showShareMenu
 *
 * 用法：Page(withShare({ ...原页面配置... }))
 * 页面自定义的 onShareAppMessage 仍优先生效；朋友圈与收藏由本模块补齐。
 */
const DEFAULT_TITLE = '叭啦·过日子'
const DEFAULT_PATH = '/pages/index/index'
const DEFAULT_IMAGE = '/assets/brand/share-card.png'

/** 开启当前页面的转发菜单（含朋友圈） */
function enableShareMenu() {
  if (typeof wx === 'undefined' || typeof wx.showShareMenu !== 'function') return
  wx.showShareMenu({
    withShareTicket: true,
    menus: ['shareAppMessage', 'shareTimeline'],
    fail: () => {},
  })
}

/** 分享标题截断，避免超长话题撑破卡片 */
function clip(title) {
  if (!title) return ''
  return title.length > 18 ? `${title.slice(0, 18)}…` : title
}

/**
 * 朋友圈 / 收藏场景不能指定 path，只能带 query。
 * 取当前页面参数，详情页会自动带上 id / eventId 等，保证打开的是同一条内容。
 */
function currentQuery() {
  try {
    const pages = getCurrentPages()
    const page = pages && pages[pages.length - 1]
    const options = (page && page.options) || {}
    return Object.keys(options)
      .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(options[key])}`)
      .join('&')
  } catch (e) {
    return ''
  }
}

/** 详情页自动带上内容标题，其他页面用品牌标题 */
function inferTitle(ctx) {
  const data = (ctx && ctx.data) || {}
  if (data.poll && data.poll.title) return clip(data.poll.title) || DEFAULT_TITLE
  if (data.club && data.club.name) return `${clip(data.club.name)} · 欢迎来看看`
  return DEFAULT_TITLE
}

function resolveTitle(ctx, custom) {
  if (typeof custom === 'function') return custom.call(ctx) || DEFAULT_TITLE
  if (typeof custom === 'string' && custom) return custom
  return inferTitle(ctx)
}

/** 生成三个分享回调，可单独用于某个页面 */
function shareConfig(options = {}) {
  const path = options.path || DEFAULT_PATH
  const imageUrl = options.imageUrl || DEFAULT_IMAGE
  const queryOf = () => (options.query !== undefined ? options.query : currentQuery())

  return {
    onShareAppMessage() {
      return {
        title: resolveTitle(this, options.title),
        path,
        imageUrl,
      }
    },

    onShareTimeline() {
      return {
        title: resolveTitle(this, options.title),
        query: queryOf(),
        imageUrl,
      }
    },

    onAddToFavorites() {
      return {
        title: resolveTitle(this, options.title),
        imageUrl,
        query: queryOf(),
      }
    },
  }
}

/**
 * 包装 Page 配置：注入分享回调并在 onLoad 时开启分享菜单。
 * 页面自己的 onShareAppMessage 优先级更高（对象展开时后者覆盖前者）。
 */
function withShare(pageOptions = {}, shareOptions = {}) {
  const originalOnLoad = pageOptions.onLoad
  return {
    ...shareConfig(shareOptions),
    ...pageOptions,
    onLoad(options) {
      enableShareMenu()
      if (originalOnLoad) originalOnLoad.call(this, options)
    },
  }
}

module.exports = {
  enableShareMenu,
  shareConfig,
  withShare,
  DEFAULT_TITLE,
  DEFAULT_PATH,
  DEFAULT_IMAGE,
}
