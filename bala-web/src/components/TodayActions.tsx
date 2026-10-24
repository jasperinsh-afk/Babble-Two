import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { EventCard } from '@/components/cards'
import { EmptyView, SectionHeader } from '@/components/common'
import type { EventInfo, MessageInfo } from '@/types/models'
import { messageTargetPath, messageTypeLabel } from '@/utils/messages'

export const HOME_ACTION_MESSAGES_KEY = ['me', 'messages', 'home-actions']

interface Props {
  messages: MessageInfo[]
  todayEvents: EventInfo[]
}

/** 今日行动区：个人消息行动 + 今日安排；数据分别来自 me.messages 与 home.feed，不混合 */
export default function TodayActions({ messages, todayEvents }: Props) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  async function openAction(message: MessageInfo) {
    const target = messageTargetPath(message)
    if (!message.readAt) {
      try {
        await api.meMarkRead({ ids: [message._id] })
        void api.analyticsTrack('message_read', {
          messageId: message._id,
          messageType: message.type,
          source: 'home_action',
        })
        await queryClient.invalidateQueries({ queryKey: HOME_ACTION_MESSAGES_KEY })
      } catch {
        /* 已读失败不打断跳转 */
      }
    }
    if (target) navigate(target)
  }

  return (
    <>
      <section className="section">
        <SectionHeader title="今日行动" />
        {messages.length ? (
          <div className="today-actions">
            {messages.map((message) => (
              <button
                type="button"
                key={message._id}
                className={`today-action ${message.readAt ? '' : 'today-action--unread'}`}
                onClick={() => void openAction(message)}
              >
                <span className="today-action__type">{messageTypeLabel(message.type)}</span>
                <span className="today-action__title">{message.title}</span>
                <span className="today-action__content">{message.content}</span>
                {message.readAt ? null : <span className="today-action__dot" aria-label="未读" />}
              </button>
            ))}
          </div>
        ) : (
          <EmptyView icon="✅" title="暂无待办事项" subtitle="有活动变更或投票结果时会在这里提醒" />
        )}
      </section>

      {todayEvents.length ? (
        <section className="section">
          <SectionHeader title="今日安排" />
          {todayEvents.map((event) => (
            <EventCard
              key={event._id}
              event={event}
              onClick={() => navigate(`/calendar?eventId=${event._id}`)}
            />
          ))}
        </section>
      ) : null}
    </>
  )
}
