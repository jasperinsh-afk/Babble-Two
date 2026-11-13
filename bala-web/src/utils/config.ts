/** 全局枚举文案（移植自 miniprogram/utils/config.js） */

export const PAGE_SIZE = 20

/**
 * 服务开通开关：当前演示阶段只有「投票」全量开放，
 * 扫码打卡与「生活」板块下的校园服务在所属校区尚未开通，
 * 点击时统一提示「校区尚未开通该服务」。全部开通后置为 true 即可放行。
 */
export const SERVICE_OPENED = false

export const pollTypeLabel: Record<string, string> = {
  single: '单选',
  multi: '多选',
  pk: 'PK',
  ranking: '排序',
  groupbuy: '接龙',
}

export const clubCategoryLabel: Record<string, string> = {
  all: '全部',
  academic: '学术',
  sports: '体育',
  art: '艺术',
  charity: '公益',
  interest: '兴趣',
  other: '其他',
}

export const rarityLabel: Record<string, string> = {
  normal: '普通',
  rare: '稀有',
  epic: '史诗',
  legendary: '传奇',
}

export const badgeRuleLabel: Record<string, string> = {
  vote_count: '累计投票',
  nfc_unique: '打卡点位',
  club_count: '加入社团',
  event_count: '报名活动',
  vote_streak: '连续投票',
}

/** 小程序页面路径 → 网页路由（Banner targetRoute 等深链兼容）；网页原生路由直接放行 */
const routeMap: Record<string, string> = {
  '/home': '/home',
  '/living': '/living',
  '/vote': '/vote',
  '/club': '/club',
  '/calendar': '/calendar',
  '/scan': '/scan',
  '/profile': '/profile',
  '/messages': '/messages',
  '/pages/index/index': '/home',
  '/pages/campus/index/index': '/campus',
  '/pages/message/index/index': '/messages',
  '/pages/vote/list/list': '/vote',
  '/pages/vote/detail/detail': '/vote',
  '/pages/club/list/list': '/club',
  '/pages/club/detail/detail': '/club',
  '/pages/calendar/index/index': '/calendar',
  '/pages/living/index/index': '/living',
  '/pages/scan/index/index': '/scan',
  '/pages/profile/index/index': '/profile',
}

export function resolveRoute(target?: string | null): string {
  if (!target) return '/home'
  const [path, query] = target.split('?')
  const mapped = routeMap[path] || '/home'
  return query ? `${mapped}?${query}` : mapped
}
