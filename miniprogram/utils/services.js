/**
 * 校园服务目录
 *
 * 投票以外的全部功能（活动 / 社团 / 生活圈 / 失物招领 / 扫码打卡）
 * 都收敛到「生活」板块，由这里统一定义名称、说明、图标字符与跳转方式，
 * 避免页面里硬编码路由。
 *
 * serviceOpened：校区开通开关。当前演示阶段只有投票全量开放，
 * 其余服务尚未在本校区开通，点击统一提示「校区尚未开通该服务」。
 * 全部开通后把这里改为 true 即可放行，无需改动页面。
 */
const serviceOpened = false

const CAMPUS_SERVICES = [
  {
    key: 'calendar',
    label: '校园活动',
    desc: '讲座、赛事与社团活动，按日历查看',
    glyph: '📅',
    mode: 'navigate',
    path: '/pages/calendar/index/index',
  },
  {
    key: 'club',
    label: '社团广场',
    desc: '加入兴趣社团，追更社团动态',
    glyph: '👥',
    mode: 'navigate',
    path: '/pages/club/list/list',
  },
  {
    key: 'circle',
    label: '生活圈',
    desc: '楼栋里的新鲜事与互助信息',
    glyph: '💬',
    mode: 'living',
    view: 'circle',
  },
  {
    key: 'lost',
    label: '失物招领',
    desc: '丢东西或捡到东西，登记一下',
    glyph: '🔍',
    mode: 'living',
    view: 'lost',
  },
  {
    key: 'scan',
    label: '扫码打卡',
    desc: '扫描点位码，收集校园勋章',
    glyph: '',
    mode: 'navigate',
    path: '/pages/scan/index/index',
  },
]

/** 生活板块内子视图 → campus-living 组件的 Tab 下标 */
const LIVING_VIEW_TAB = {
  circle: 0,
  lost: 1,
}

function findService(key) {
  return CAMPUS_SERVICES.find((service) => service.key === key)
}

module.exports = {
  serviceOpened,
  CAMPUS_SERVICES,
  LIVING_VIEW_TAB,
  findService,
}
