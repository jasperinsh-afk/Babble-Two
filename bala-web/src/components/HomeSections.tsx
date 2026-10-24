import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { ClubCard, EventCard } from '@/components/cards'
import { SectionHeader } from '@/components/common'
import type { HomeFeed, HomeSection } from '@/types/models'
import { countdownText } from '@/utils/format'

export const DEFAULT_HOME_SECTIONS: HomeSection[] = [
  { id: 'section-banner', type: 'banner', title: 'Banner 轮播', enabled: true, config: { limit: 5 } },
  { id: 'section-today', type: 'todayPoll', title: '今日投票', enabled: true, config: {} },
  {
    id: 'section-quick', type: 'quickEntries', title: '快捷入口', enabled: true,
    config: { items: [
      { key: 'vote', label: '投票', icon: '✓', to: '/vote' },
      { key: 'club', label: '社团', icon: '⌂', to: '/club' },
      { key: 'calendar', label: '日历', icon: '▦', to: '/calendar' },
      { key: 'living', label: '住宿', icon: '⌂', to: '/living' },
      { key: 'scan', label: '扫码', icon: '◎', to: '/scan' },
    ] },
  },
  { id: 'section-hot', type: 'hotPolls', title: '热门投票', enabled: true, config: { limit: 5 } },
  { id: 'section-events', type: 'events', title: '推荐活动', enabled: true, config: { limit: 3 } },
  { id: 'section-clubs', type: 'clubs', title: '社团精选', enabled: true, config: { limit: 6 } },
]

interface Props {
  section: HomeSection
  feed: HomeFeed
  banner: ReactNode
}

export function HomeSection({ section, feed, banner }: Props) {
  const navigate = useNavigate()
  if (!section.enabled) return null
  const title = section.title
  const limit = Math.min(20, Math.max(1, section.config.limit || 5))

  if (section.type === 'banner') return feed.banners.length ? <div key={section.id}>{banner}</div> : null

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
          {entries.map((entry) => (
            <button type="button" key={entry.key} className="home-quick__item" onClick={() => navigate(entry.to)}>
              <span className={`home-quick__icon home-quick__icon--${entry.key}`}>{entry.icon}</span>
              <span className="home-quick__label">{entry.label}</span>
            </button>
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
