import type { ComponentType, ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ClubCard, EventCard } from '@/components/cards'
import { SectionHeader } from '@/components/common'
import { CalendarIcon, LivingIcon, ScanIcon, VoteIcon } from '@/components/icons'
import { useOpenService } from '@/components/services'
import type { HomeFeed, HomeSection as HomeSectionType } from '@/types/models'
import { SERVICE_OPENED } from '@/utils/config'
import { countdownText } from '@/utils/format'

/** 后端未下发配置时的首页版块（活动 / 社团已收敛到校园服务目录） */
export const DEFAULT_HOME_SECTIONS: HomeSectionType[] = [
  {
    id: 'section-quick',
    type: 'quickEntries',
    title: '快捷入口',
    enabled: true,
    config: {
      items: [
        { key: 'days', label: '日子', icon: '📅', to: '/days' },
        { key: 'vote', label: '投票广场', icon: '🗳️', to: '/vote' },
      ],
    },
  },
  { id: 'section-today', type: 'todayPoll', title: '今日必投', enabled: true, config: {} },
  { id: 'section-recent', type: 'recentPolls', title: '最近投票', enabled: true, config: { limit: 5 } },
  { id: 'section-hot', type: 'hotPolls', title: '热门投票', enabled: true, config: { limit: 5 } },
]

const ENTRY_GLYPHS: Record<string, ComponentType<{ className?: string }>> = {
  days: CalendarIcon,
  vote: VoteIcon,
  living: LivingIcon,
  scan: ScanIcon,
}

interface Props {
  section: HomeSectionType
  feed: HomeFeed
  banner?: ReactNode
}

export function HomeSection({ section, feed, banner }: Props) {
  const navigate = useNavigate()
  const openService = useOpenService()
  if (!section.enabled) return null
  const title = section.title
  const limit = Math.min(20, Math.max(1, section.config.limit || 5))

  if (section.type === 'banner') return banner ? <>{banner}</> : null

  if (section.type === 'todayPoll') {
    const poll = feed.todayPoll
    return poll ? (
      <section className="section fade-up">
        <SectionHeader title={title} />
        <div className="home-today pressable" onClick={() => navigate(`/vote/${poll._id}`)} role="presentation">
          <span className="home-today__border" />
          <div className="home-today__content">
            <div className="home-today__title ellipsis">{poll.title}</div>
            <div className="home-today__count">{poll.totalVotes || 0} 人参与 · {countdownText(poll.endAt)}</div>
            <span className="home-today__btn">立即投票</span>
          </div>
        </div>
      </section>
    ) : null
  }

  if (section.type === 'quickEntries') {
    const entries = section.config.items || []
    return entries.length ? (
      <section className="section">
        <div className="home-quick">
          {entries.map((entry) => {
            const Glyph = ENTRY_GLYPHS[entry.key]
            return (
              <button
                type="button"
                key={entry.key}
                className={`home-quick__item home-quick__item--${entry.key}`}
                onClick={() => {
                  if (!openService(entry.key)) navigate(entry.to)
                }}
              >
                <span className={`home-quick__icon home-quick__icon--${entry.key}`}>
                  {Glyph ? <Glyph className="home-quick__glyph" /> : entry.icon}
                </span>
                <span className="home-quick__text">
                  <span className="home-quick__label">{entry.label}</span>
                  <span className="home-quick__hint">
                    {entry.key === 'days'
                      ? '记录重要的日子'
                      : entry.key === 'vote'
                        ? '看看大家在投什么'
                        : SERVICE_OPENED
                          ? '进去逛逛'
                          : '尚未开通'}
                  </span>
                </span>
              </button>
            )
          })}
        </div>
      </section>
    ) : null
  }

  if (section.type === 'recentPolls') {
    const polls = (feed.recentPolls ?? []).slice(0, limit)
    return polls.length ? (
      <section className="section">
        <SectionHeader title={title} actionText="全部" onAction={() => navigate('/vote')} />
        <div className="home-recent">
          {polls.map((poll) => (
            <div
              className="home-recent__item pressable"
              key={poll._id}
              onClick={() => navigate(`/vote/${poll._id}`)}
              role="presentation"
            >
              <div className="home-recent__body">
                <div className="home-recent__title ellipsis">{poll.title}</div>
                <div className="home-recent__meta">
                  {poll.totalVotes || 0} 人参与
                  {poll.endAt ? ` · ${countdownText(poll.endAt)}` : ''}
                </div>
              </div>
              <span className="home-recent__go">去投票 ›</span>
            </div>
          ))}
        </div>
      </section>
    ) : null
  }

  if (section.type === 'hotPolls') {
    const polls = feed.hotPolls.slice(0, limit)
    return polls.length ? (
      <section className="section">
        <SectionHeader title={title} actionText="全部" onAction={() => navigate('/vote')} />
        <div className="home-scroll"><div className="home-scroll__wrap">
          {polls.map((poll) => (
            <div className="home-poll-mini pressable" key={poll._id} onClick={() => navigate(`/vote/${poll._id}`)} role="presentation">
              <div className="home-poll-mini__title ellipsis-2">{poll.title}</div>
              <div className="home-poll-mini__count">{poll.totalVotes || 0} 已投</div>
            </div>
          ))}
        </div></div>
      </section>
    ) : null
  }

  if (section.type === 'events') {
    const events = feed.events.slice(0, limit)
    return events.length ? (
      <section className="section">
        <SectionHeader title={title} actionText="日历" onAction={() => navigate('/calendar')} />
        {events.map((event) => <EventCard key={event._id} event={event} onClick={() => navigate(`/calendar?eventId=${event._id}`)} />)}
      </section>
    ) : null
  }

  if (section.type === 'clubs') {
    const clubs = feed.clubs.slice(0, limit)
    return clubs.length ? (
      <section className="section">
        <SectionHeader title={title} actionText="全部" onAction={() => navigate('/club')} />
        <div className="grid-2">{clubs.map((club) => <ClubCard key={club._id} club={club} onClick={() => navigate(`/club/${club._id}`)} />)}</div>
      </section>
    ) : null
  }
  return null
}
