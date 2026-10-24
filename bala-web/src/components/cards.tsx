import type { Club, EventInfo, Poll } from '@/types/models'
import { clubCategoryLabel, pollTagLabel, pollTypeLabel } from '@/utils/config'
import { compactNumber, countdownText, dateTimeText } from '@/utils/format'
import { SmartImage } from './common'

/** 投票卡片（对应 components/poll-card） */
export function PollCard({ poll, onClick }: { poll: Poll; onClick?: () => void }) {
  const total = poll.totalVotes || 0
  const isChain = poll.pollType === 'groupbuy'
  const joinPercent =
    isChain && poll.maxParticipants
      ? Math.min(100, Math.round(((poll.participantCount || 0) / poll.maxParticipants) * 100))
      : 0

  return (
    <article className="poll-card pressable" onClick={onClick}>
      <div className="poll-card__header">
        <span className="poll-card__type chip">{pollTypeLabel[poll.pollType] || '投票'}</span>
        <span className="poll-card__tag chip">{pollTagLabel[poll.tag || ''] || poll.tag || ''}</span>
        <span className="grow" />
        <span className="poll-card__count">{compactNumber(total)} 已投</span>
      </div>
      <h3 className="poll-card__title ellipsis-2">{poll.title}</h3>
      {poll.description ? <p className="poll-card__desc">{poll.description}</p> : null}
      <div className="poll-card__footer">
        <span className="poll-card__time">
          {poll.endAt ? `剩 ${countdownText(poll.endAt)}` : ''}
        </span>
        {isChain && poll.maxParticipants ? (
          <div className="poll-card__progress">
            <div className="poll-card__progress-bar">
              <div className="poll-card__progress-fill" style={{ width: `${joinPercent}%` }} />
            </div>
            <span className="poll-card__progress-text">
              {poll.participantCount || 0}/{poll.maxParticipants || '∞'}
            </span>
          </div>
        ) : null}
      </div>
    </article>
  )
}

/** 社团宫格卡片（对应 components/club-card） */
export function ClubCard({ club, onClick }: { club: Club; onClick?: () => void }) {
  return (
    <article className="club-card pressable" onClick={onClick}>
      <SmartImage
        className="club-card__cover"
        src={club.coverUrl}
        alt={club.name}
        fallback={<span>{(club.name || '社').charAt(0)}</span>}
      />
      <div className="club-card__body">
        <div className="club-card__title-row">
          <span className="club-card__name ellipsis">{club.name}</span>
          {club.isVerified ? <span className="club-card__badge">V</span> : null}
        </div>
        <div className="club-card__meta">
          <span className="club-card__category">
            {clubCategoryLabel[club.category || ''] || club.category || ''}
          </span>
          <span className="club-card__count">{club.memberCount || 0} 成员</span>
        </div>
      </div>
    </article>
  )
}

/** 活动横向卡片（对应 components/event-card） */
export function EventCard({ event, onClick }: { event: EventInfo; onClick?: () => void }) {
  const endAt = event.endAt || event.startAt
  const countText = event.maxParticipants
    ? `${event.participantCount || 0}/${event.maxParticipants} 报名`
    : `${event.participantCount || 0} 人已报名`

  return (
    <article className="event-card pressable" onClick={onClick}>
      <SmartImage
        className="event-card__thumb"
        src={event.coverUrl}
        alt={event.title}
        fallback={<span>{(event.title || '活').charAt(0)}</span>}
      />
      <div className="event-card__body">
        <h3 className="event-card__title ellipsis">{event.title}</h3>
        <div className="event-card__row">
          <span className="event-card__meta">
            {event.startAt ? `${dateTimeText(event.startAt)} · ${countdownText(endAt)}` : ''}
          </span>
        </div>
        {event.location ? (
          <div className="event-card__row">
            <span className="event-card__meta">📍 {event.location}</span>
          </div>
        ) : null}
        <div className="event-card__count">
          <span className="event-card__chip chip chip--solid">{countText}</span>
        </div>
      </div>
    </article>
  )
}
