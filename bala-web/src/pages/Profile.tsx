import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { EmptyView, SectionHeader, Skeleton } from '@/components/common'
import { TabBar } from '@/components/chrome'
import { badgeRuleLabel } from '@/utils/config'
import { dateText, fromNowText } from '@/utils/format'
import { toast } from '@/utils/feedback'
import { getSession } from '@/utils/identity'

export default function Profile() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['me', 'overview'],
    queryFn: () => api.meOverview(),
  })
  const { data: health } = useQuery({
    queryKey: ['web', 'health'],
    queryFn: () => api.health(),
    staleTime: Infinity,
  })
  const { data: link, refetch: refetchLink } = useQuery({
    queryKey: ['web', 'link'],
    queryFn: () => api.linkStatus(),
    staleTime: 30_000,
  })
  const [code, setCode] = useState('')
  const [binding, setBinding] = useState(false)

  async function handleBind() {
    const digits = code.replace(/\D/g, '')
    if (digits.length !== 6) {
      toast('请输入小程序里显示的 6 位绑定码')
      return
    }
    setBinding(true)
    try {
      await api.bindAccount(digits)
      setCode('')
      toast('绑定成功，两端数据已互通')
      await refetchLink()
      await queryClient.invalidateQueries()
    } catch (error) {
      toast(error instanceof Error ? error.message : '绑定失败，请稍后重试')
    } finally {
      setBinding(false)
    }
  }

  async function handleUnbind() {
    setBinding(true)
    try {
      await api.unbindAccount()
      toast('已解除绑定')
      await refetchLink()
      await queryClient.invalidateQueries()
    } catch (error) {
      toast(error instanceof Error ? error.message : '解绑失败，请稍后重试')
    } finally {
      setBinding(false)
    }
  }

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

      <section className="section">
        <SectionHeader title="账号互通" />
        <div className="card link-card">
          {link?.bound ? (
            <>
              <div className="link-card__status link-card__status--on">
                已绑定小程序账号（{link.openid}）
              </div>
              <p className="link-card__desc">
                网页端的投票、达人分、日程已与小程序共用同一份数据。
              </p>
              <button
                className="link-card__btn link-card__btn--ghost"
                disabled={binding}
                onClick={handleUnbind}
              >
                解除绑定
              </button>
            </>
          ) : (
            <>
              <p className="link-card__desc">
                在小程序「我的 → 绑定网页端」获取 6 位码，输入后两端数据互通。
              </p>
              <div className="link-card__row">
                <input
                  className="link-card__input"
                  value={code}
                  inputMode="numeric"
                  maxLength={6}
                  placeholder="6 位绑定码"
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                />
                <button
                  className="link-card__btn link-card__btn--primary"
                  disabled={binding}
                  onClick={handleBind}
                >
                  {binding ? '绑定中…' : '绑定'}
                </button>
              </div>
              {link?.mode === 'local' ? (
                <p className="link-card__hint">
                  当前是本地演示库，需配置 AppSecret 切到云数据库后才能绑定。
                </p>
              ) : null}
            </>
          )}
        </div>
      </section>

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
