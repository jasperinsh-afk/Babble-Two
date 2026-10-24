/**
 * 全局配置
 *
 * cloudEnv：微信云开发环境 ID。请在微信开发者工具「云开发」控制台创建环境后，
 * 把环境 ID 填到这里（形如 goqd-prod-1x2y3z）。
 * 留空表示使用默认环境（仅当只有一个环境时可用）。
 */
module.exports = {
  cloudEnv: 'cloud1-d1gz1h52b5f884504',

  // 分页大小，与云函数 PAGE_SIZE 保持一致
  pageSize: 20,

  // 投票类型 → 展示文案
  pollTypeLabel: {
    single: '单选',
    multi: '多选',
    pk: 'PK',
    ranking: '排序',
    groupbuy: '接龙',
  },

  // 投票标签 → 展示文案（列表筛选胶囊）
  pollTagLabel: {
    all: '全部',
    news: '时事',
    campus: '学习',
    meme: '热梗',
    group: '接龙',
  },

  // 社团分类 → 展示文案
  clubCategoryLabel: {
    all: '全部',
    academic: '学术',
    sports: '体育',
    art: '艺术',
    charity: '公益',
    interest: '兴趣',
    other: '其他',
  },

  // 勋章稀有度 → 展示文案
  rarityLabel: {
    normal: '普通',
    rare: '稀有',
    epic: '史诗',
    legendary: '传奇',
  },

  // 勋章规则类型 → 展示文案
  badgeRuleLabel: {
    vote_count: '累计投票',
    nfc_unique: '打卡点位',
    club_count: '加入社团',
    event_count: '报名活动',
    vote_streak: '连续投票',
  },
}
