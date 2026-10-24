import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { EmptyView, Skeleton, SmartImage } from '@/components/common'
import { TabBar } from '@/components/chrome'
import { DEFAULT_HOME_SECTIONS, HomeSection } from '@/components/HomeSections'
import TodayActions, { HOME_ACTION_MESSAGES_KEY } from '@/components/TodayActions'
import type { HomeFeed } from '@/types/models'
import { resolveRoute } from '@/utils/config'
import { dateText } from '@/utils/format'
import { ACTION_MESSAGE_TYPES } from '@/utils/messages'

const CACHE_KEY = 'bala_home_feed'
const CACHE_MAX_AGE = 10 * 60 * 1000

let feedViewTracked = false

function readCache(): { time: number; data: HomeFeed } | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (Date.now() - parsed.time > CACHE_MAX_AGE) return null
    return parsed
  } catch {
    return null
  }
}

function BannerCarousel({ banners }: { banners: HomeFeed['banners'] }) {
  const [index, setIndex] = useState(0)
  const navigate = useNavigate()
  const count = banners.length

  useEffect(() => {
    if (count < 2) return
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % count), 5000)
    return () => window.clearInterval(timer)
  }, [count])

  if (!count) return null
  const current = banners[Math.min(index, count - 1)]

  return (
    <div className="home-banner">
      <div
        className="home-banner__track"
        style={{ transform: `translateX(-${Math.min(index, count - 1) * 100}%)` }}
      >
        {banners.map((banner) => (
          <div
            className="home-banner__item"
            key={banner._id}
            onClick={() => banner.targetRoute && navigate(resolveRoute(banner.targetRoute))}
            role="presentation"
          >
            <SmartImage className="home-banner__img" src={banner.imageUrl} alt={banner.title} />
            <div className="home-banner__shade">
              <span className="home-banner__title">{banner.title}</span>
            </div>
          </div>
        ))}
      </div>
      {count > 1 ? (
        <div className="home-banner__dots">
          {banners.map((banner, i) => (
            <button
              key={banner._id}
              type="button"
              aria-label={`第 ${i + 1} 张`}
              className={`home-banner__dot ${i === Math.min(index, count - 1) ? 'is-active' : ''}`}
              onClick={() => setIndex(i)}
            />
          ))}
        </div>
      ) : null}
      <span className="sr-only">{current.title}</span>
    </div>
  )
}

export default function Home() {
  const navigate = useNavigate()
  const cached = readCache()

  const { data, isLoading } = useQuery({
    queryKey: ['home', 'feed'],
    queryFn: () => api.homeFeed({ silent: true }),
    initialData: cached?.data,
    initialDataUpdatedAt: cached?.time,
  })

  const { data: messageData } = useQuery({
    queryKey: HOME_ACTION_MESSAGES_KEY,
    queryFn: () => api.meMessages({}, { silent: true }),
    staleTime: 0,
  })

  useEffect(() => {
    if (feedViewTracked) return
    feedViewTracked = true
    void api.analyticsTrack('feed_view', { source: 'web_home' })
  }, [])

  useEffect(() => {
    if (!data) return
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ time: Date.now(), data }))
    } catch {
      /* 缓存失败不影响展示 */
    }
  }, [data])

  const loading = isLoading && !data
  const banners = data?.banners ?? []
  const sections = data?.sections?.length ? data.sections : DEFAULT_HOME_SECTIONS
  const actionMessages = (messageData?.list ?? []).filter((message) =>
    ACTION_MESSAGE_TYPES.includes(message.type),
  )
  const todayEvents = (data?.events ?? []).filter(
    (event) => dateText(event.startAt) === dateText(new Date()),
  )
  const unread = messageData?.unread ?? 0

  return (
    <div className="page page--home">
      <div className="home-header">
        <div className="home-header__brand">
          <img className="home-header__mark" src="/assets/brand/logo-mark.png" alt="叭啦" />
          <span className="home-header__logo">叭啦</span>
          <span className="home-header__tag">Babble</span>
        </div>
        <button
          type="button"
          className="home-header__scan"
          aria-label="扫码打卡"
          onClick={() => navigate('/scan')}
        >
          <span className="home-header__scan-dot" />
        </button>
      </div>

      <TodayActions messages={actionMessages} todayEvents={todayEvents} />

      {loading ? (
        <div className="home-skeleton">
          <Skeleton className="home-skeleton__banner" />
          <div className="home-skeleton__row">
            <Skeleton className="home-skeleton__card" />
            <Skeleton className="home-skeleton__card" />
          </div>
        </div>
      ) : (
        <>
          {data ? sections.map((section) => (
            <HomeSection
              key={section.id}
              section={section}
              feed={data}
              banner={<BannerCarousel banners={banners.slice(0, section.config.limit || 5)} />}
            />
          )) : null}

          {!loading && !data ? (
            <EmptyView
              icon="📡"
              title="暂时连不上服务"
              subtitle="请确认后端已启动（uvicorn 8000 端口），下拉或刷新重试"
            />
          ) : null}
        </>
      )}
      <TabBar badges={{ '/messages': unread }} />
    </div>
  )
}
