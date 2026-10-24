import type { MessageInfo, MessageType } from '@/types/models'

/** 今日行动区只渲染有明确行动指向的消息；deadline 暂无产生源，不展示 */
export const ACTION_MESSAGE_TYPES: MessageType[] = [
  'event_change',
  'event_cancelled',
  'poll_result',
  'owner_response',
]

const MESSAGE_TYPE_LABELS: Record<MessageType, string> = {
  event_change: '活动变更',
  event_cancelled: '活动取消',
  poll_result: '投票结果',
  owner_response: '收到回复',
  deadline: '即将截止',
}

export function messageTypeLabel(type: string): string {
  return MESSAGE_TYPE_LABELS[type as MessageType] || '消息'
}

/** 与现有路由机制对齐：活动回跳日历并自动打开详情，投票回跳投票详情 */
export function messageTargetPath(message: Pick<MessageInfo, 'refType' | 'refId'>): string | null {
  if (!message.refId) return null
  if (message.refType === 'event') return `/calendar?eventId=${message.refId}`
  if (message.refType === 'poll') return `/vote/${message.refId}`
  return null
}
