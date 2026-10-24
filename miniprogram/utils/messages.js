/** 消息类型标签与行动跳转规则（与 Web src/utils/messages.ts 保持一致） */

/** 今日行动区只渲染有明确行动指向的消息；deadline 暂无产生源，不展示 */
const ACTION_MESSAGE_TYPES = [
  'event_change',
  'event_cancelled',
  'poll_result',
  'owner_response',
]

const MESSAGE_TYPE_LABELS = {
  event_change: '活动变更',
  event_cancelled: '活动取消',
  poll_result: '投票结果',
  owner_response: '收到回复',
  deadline: '即将截止',
}

function messageTypeLabel(type) {
  return MESSAGE_TYPE_LABELS[type] || '消息'
}

/** 与现有路由机制对齐：活动回跳日历并自动打开详情，投票回跳投票详情 */
function messageTargetPath(message) {
  if (!message || !message.refId) return null
  if (message.refType === 'event') return `/pages/calendar/index/index?eventId=${message.refId}`
  if (message.refType === 'poll') return `/pages/vote/detail/detail?id=${message.refId}`
  return null
}

module.exports = { ACTION_MESSAGE_TYPES, messageTypeLabel, messageTargetPath }
