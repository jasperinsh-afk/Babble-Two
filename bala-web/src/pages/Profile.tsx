import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { EmptyView, SectionHeader, Skeleton } from '@/components/common'
import { TabBar } from '@/components/chrome'
import { badgeRuleLabel } from '@/utils/config'
import { dateText, fromNowText } from '@/utils/format'
import { getSession } from '@/utils/identity'

export default function Profile() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['me', 'overview'],
    queryFn: () => api.meOverview(),
  })
  const { data: health } = useQuery({
    queryKey: ['web', 'health'],
    queryFn: () => api.health(),
    staleTime: Infinity,
  })

  const stats = data?.stats
  const badges = data?.badges ?? []
  const recentVotes = data?.recentVotes ?? []
  const recentCheckins = data?.recentCheckins ?? []
  const identity = getSession()?.identity || ''

  return (
    <div className="page page--profile">
      <div className="profile-header">
        <div className="profile-header__title">本地足迹</div>
        <div className="profile-header__subtitle">你的兴趣数字足迹</div>
      </div>

      <div className="profile-stats card section">
        <div className="profile-stat">
          <span className="profile-stat__num">{stats?.voteCount || 0}</span>
          <span className="profile-stat__label">参与投票</span>
        </div>
        <span className="profile-stat__divider" />
        <div className="profile-stat">
          <span className="profile-stat__num">{stats?.checkinCount || 0}</span>
          <span className="profile-stat__label">扫码打卡</span>
        </div>
        <span className="profile-stat__divider" />
        <div className="profile-stat">
          <span className="profile-stat__num">{stats?.badgeCount || 0}</span>
          <span className="profile-stat__label">获得勋章</span>
        </div>
      </div>

      <section className="section">
        <SectionHeader title="勋章墙" />
        {isLoading ? (
          <Skeleton style={{ height: 150 }} />
        ) : (
          <div className="profile-badges">
            {badges.map((badge) => (
              <div
                className={`profile-badge ${badge.unlocked ? 'profile-badge--unlocked' : 'profile-badge--locked'}`}
                key={badge.code}
              >
                <div className="profile-badge__icon">
                  {badge.unlocked ? (
                    <span>
                      {badge.icon ||
                        (badge.code === 'scan_explorer' ? '◎' : badge.code === 'club_pioneer' ? '⌂' : '★')}
                    </span>
                  ) : (
                    <span>🔒</span>
                  )}
                </div>
                <div className="profile-badge__name">{badge.name}</div>
                <div className="profile-badge__desc">
                  {badge.description ||
                    `${badgeRuleLabel[badge.rule?.type || ''] || '累计'} ≥ ${badge.rule?.count || 0}`}
                </div>
                {badge.unlocked && badge.earnedAt ? (
                  <div className="profile-badge__earned">{dateText(badge.earnedAt)}</div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>

      {recentVotes.length ? (
        <section className="section">
          <SectionHeader title="最近投票" />
          <div className="profile-foot">
            {recentVotes.map((vote) => (
              <div
                className="profile-foot__item pressable"
                key={vote.pollId}
                onClick={() => navigate(`/vote/${vote.pollId}`)}
                role="presentation"
              >
                <span className="profile-foot__dot profile-foot__dot--vote" />
                <div className="profile-foot__body">
                  <div className="profile-foot__title ellipsis">{vote.title}</div>
                  <div className="profile-foot__time">{fromNowText(vote.createdAt)}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {recentCheckins.length ? (
        <section className="section">
          <SectionHeader title="最近打卡" />
          <div className="profile-foot">
            {recentCheckins.map((checkin) => (
              <div className="profile-foot__item" key={checkin.cardId}>
                <span className="profile-foot__dot profile-foot__dot--scan" />
                <div className="profile-foot__body">
                  <div className="profile-foot__title">{checkin.cardId}</div>
                  <div className="profile-foot__time">
                    {fromNowText(checkin.lastTapAt)} · 累计 {checkin.tapCount} 次
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      {!isLoading && !recentVotes.length && !recentCheckins.length ? (
        <section className="section">
          <EmptyView icon="👣" title="暂无足迹" subtitle="去投票或扫码打卡，留下你的兴趣印记" />
        </section>
      ) : null}

      <div className="profile-meta">
        <span>
          数据源：{health?.mode === 'cloud' ? '微信云数据库（与小程序共享）' : '本地演示库（未配置 AppSecret）'}
        </span>
        {identity ? <span className="profile-meta__id">匿名身份 {identity.slice(0, 12)}…</span> : null}
      </div>
      <TabBar />
    </div>
  )
}
