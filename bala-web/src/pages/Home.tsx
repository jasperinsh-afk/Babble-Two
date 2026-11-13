import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { EmptyView } from '@/components/common'
import { TabBar } from '@/components/chrome'
import HomeHero from '@/components/HomeHero'
import { ScanIcon } from '@/components/icons'
import { useOpenService } from '@/components/services'
import { DEFAULT_HOME_SECTIONS, HomeSection } from '@/components/HomeSections'
import TodayActions, { HOME_ACTION_MESSAGES_KEY } from '@/components/TodayActions'
import type { Banner, HomeFeed } from '@/types/models'
import { dateText } from '@/utils/format'
import { ACTION_MESSAGE_TYPES } from '@/utils/messages'

const CACHE_KEY = 'bala_home_feed'
const CACHE_MAX_AGE = 10 * 60 * 1000

/** 后端不可用时的演示 Banner，保证首页版式在任何环境都成立 */
const DEMO_BANNERS: Banner[] = [
  {
    _id: 'demo-1',
    title: '全校最有梗的投票社区',
    desc: '每天一个话题，说出你的态度',
    tag: '热门',
    imageUrl: '',
    targetRoute: '/vote',
  },
  {
    _id: 'demo-2',
    title: '今天中午吃什么？',
    desc: '食堂窗口由你一票决定',
    tag: '今日',
    imageUrl: '',
    targetRoute: '/vote',
  },
  {
    _id: 'demo-3',
    title: '社团招新季 · 你来 Pick',
    desc: '想去哪儿，投一票就知道',
    tag: '社团',
    imageUrl: '',
    targetRoute: '/vote',
  },
]

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

export default function Home() {
  const openService = useOpenService()
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
  const heroBanners: Banner[] = banners.length ? banners : DEMO_BANNERS
  const sections = data?.sections?.length ? data.sections : DEFAULT_HOME_SECTIONS
  // Banner 由 HomeHero 统一承载；推荐活动 / 社团精选已并入「生活」板块
  const visibleSections = sections.filter(
    (section) => section.type !== 'banner' && section.type !== 'events' && section.type !== 'clubs',
  )
  const actionMessages = (messageData?.list ?? []).filter((message) =>
    ACTION_MESSAGE_TYPES.includes(message.type),
  )
  const todayEvents =
    data?.calendarEvents?.today ??
    (data?.events ?? []).filter((event) => dateText(event.startAt) === dateText(new Date()))
  const upcomingCalendar = data?.calendarEvents?.upcoming ?? []
  const announcements = data?.announcements ?? []
  const unread = messageData?.unread ?? 0

  return (
    <div className="page page--home">
      <header className="home-top">
        <div className="home-top__brand">
          <img className="home-top__mark" src="/assets/brand/logo-mark.png" alt="叭啦" />
          <div className="home-top__titles"><span className="home-top__logo">叭啦</span></div>
        </div>
        <button
          type="button"
          className="scan-btn"
          aria-label="扫码打卡"
          onClick={() => openService('scan')}
        >
          <ScanIcon className="scan-btn__icon" />
          <span className="scan-btn__text">扫码</span>
        </button>
      </header>

      {announcements.length ? (
        <div className="home-notice-stack">
          {announcements.map((item) => (
            <div
              key={item._id}
              className={`home-notice home-notice--${item.level || 'info'}`}
              role="note"
            >
              <span className="home-notice__badge">
                {item.level === 'urgent' ? '紧急公告' : item.level === 'important' ? '重要公告' : '公告'}
              </span>
              <div className="home-notice__body">
                <span className="home-notice__title">{item.title}</span>
                {item.content ? <span className="home-notice__content">{item.content}</span> : null}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      <HomeHero banners={heroBanners} loading={loading} />

      {loading ? null : (
        <>
          {data ? (
            visibleSections.map((section) => (
              <HomeSection key={section.id} section={section} feed={data} />
            ))
          ) : null}

          <TodayActions
            messages={actionMessages}
            todayEvents={todayEvents}
            upcomingEvents={upcomingCalendar}
          />

          {!data ? (
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
