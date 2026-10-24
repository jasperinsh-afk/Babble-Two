import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useLoading, useToasts } from '@/utils/feedback'

const TABS = [
  { path: '/home', icon: 'home', text: '今日' },
  { path: '/campus', icon: 'campus', text: '校园' },
  { path: '/messages', icon: 'message', text: '消息' },
  { path: '/profile', icon: 'profile', text: '我的' },
]

function isTabActive(path: string, pathname: string) {
  if (path === '/home') return pathname === '/home' || pathname === '/'
  if (path === '/campus') {
    return (
      pathname.startsWith('/campus') ||
      pathname.startsWith('/vote') ||
      pathname.startsWith('/club') ||
      pathname.startsWith('/calendar') ||
      pathname.startsWith('/living')
    )
  }
  return pathname.startsWith(path)
}

/** 底部 TabBar（对应 custom-tab-bar，毛玻璃 + 选中胶囊上浮） */
export function TabBar({ badges }: { badges?: Record<string, number> }) {
  const { pathname } = useLocation()
  return (
    <nav className="tab-bar shell-fixed" aria-label="主导航">
      {TABS.map((tab) => {
        const active = isTabActive(tab.path, pathname)
        const badge = badges?.[tab.path] || 0
        return (
          <NavLink
            key={tab.path}
            to={tab.path}
            className={`tab-bar__item ${active ? 'tab-bar__item--active' : ''}`}
            aria-current={active ? 'page' : undefined}
          >
            <img
              className="tab-bar__icon"
              src={`/assets/tabbar/${tab.icon}${active ? '_active' : ''}.png`}
              alt=""
            />
            <span className="tab-bar__label">{tab.text}</span>
            {badge > 0 ? (
              <span className="tab-bar__badge" aria-label={`${badge} 条未读`}>
                {badge > 99 ? '99+' : badge}
              </span>
            ) : null}
          </NavLink>
        )
      })}
    </nav>
  )
}

/** 顶部紫色导航栏（对应 app.json window 配置，标题统一「叭啦」） */
export function TopBar({ title = '叭啦', back = false }: { title?: string; back?: boolean }) {
  const navigate = useNavigate()
  return (
    <header className="top-bar">
      {back ? (
        <button
          type="button"
          className="top-bar__back"
          aria-label="返回"
          onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/home'))}
        >
          ‹
        </button>
      ) : null}
      <span className="top-bar__title">{title}</span>
    </header>
  )
}

/** 开发后台入口（齿轮）：统一跳 /admin，未登录时由后台自行重定向到登录页 */
export function AdminGear() {
  return (
    <a className="admin-fab" href="/admin" aria-label="开发后台" title="开发后台">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="3.1" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1.08 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
      </svg>
    </a>
  )
}

export function FeedbackHost() {
  const toasts = useToasts()
  const loading = useLoading()
  return (
    <>
      <div className="toast-host" aria-live="polite">
        {toasts.map((item) => (
          <div className="toast" key={item.id}>
            {item.text}
          </div>
        ))}
      </div>
      {loading.visible ? (
        <div className="loading-mask" role="status" aria-label={loading.text}>
          <div className="loading-mask__box">
            <div className="loading-mask__spinner" />
            <span>{loading.text}</span>
          </div>
        </div>
      ) : null}
    </>
  )
}
