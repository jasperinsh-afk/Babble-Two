import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '@/api/endpoints'
import { EmptyView, SectionHeader, Skeleton } from '@/components/common'
import { TabBar } from '@/components/chrome'
import type { MessageInfo, MessagePrefs } from '@/types/models'
import { fromNowText } from '@/utils/format'
import { messageTargetPath, messageTypeLabel } from '@/utils/messages'

/** me.messages / me.markRead / me.messagePrefs 已就绪，直接读取真实数据 */
const MESSAGE_API_READY = true

const PREF_ITEMS: Array<{ key: keyof MessagePrefs; label: string }> = [
  { key: 'eventChange', label: '活动变更' },
  { key: 'eventCancel', label: '活动取消' },
  { key: 'pollResult', label: '投票结果' },
  { key: 'ownerResponse', label: '收到回复' },
  { key: 'deadline', label: '即将截止' },
]

export default function Messages() {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<MessageInfo[]>([])
  const [cursor, setCursor] = useState('')
  const [hasMore, setHasMore] = useState(false)
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [prefs, setPrefs] = useState<MessagePrefs | null>(null)
  const [savingPref, setSavingPref] = useState<keyof MessagePrefs | ''>('')

  useEffect(() => {
    let active = true

    async function loadMessages(reset = true) {
      if (!MESSAGE_API_READY) {
        if (active) setLoaded(true)
        return
      }
      if (loading) return
      setLoading(true)
      try {
        const res = await api.meMessages(reset ? {} : cursor ? { cursor } : {})
        if (!active) return
        setMessages((prev) => (reset ? res.list : [...prev, ...res.list]))
        const last = res.list[res.list.length - 1]
        setCursor(last ? last.createdAt : cursor)
        setHasMore(res.hasMore)
        setUnread(res.unread)
      } catch {
        /* api 已静默处理错误；保留空态避免伪造数据 */
      } finally {
        if (active) {
          setLoaded(true)
          setLoading(false)
        }
      }
    }

    async function loadPrefs() {
      if (!MESSAGE_API_READY) return
      try {
        const res = await api.meMessagePrefs()
        if (active) setPrefs(res.prefs)
      } catch {
        /* 偏好失败不影响消息列表 */
      }
    }

    void loadMessages(true)
    void loadPrefs()
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function openMessage(message: MessageInfo) {
    const target = messageTargetPath(message)
    if (!message.readAt) {
      try {
        await api.meMarkRead({ ids: [message._id] })
        setMessages((prev) =>
          prev.map((item) =>
            item._id === message._id ? { ...item, readAt: new Date().toISOString() } : item,
          ),
        )
        setUnread((prev) => Math.max(0, prev - 1))
        void api.analyticsTrack('message_read', {
          messageId: message._id,
          messageType: message.type,
        })
      } catch {
        /* 已读失败不打断跳转 */
      }
    }
    if (target) navigate(target)
  }

  async function togglePref(key: keyof MessagePrefs) {
    if (!prefs || savingPref) return
    const previous = prefs
    const next = { ...prefs, [key]: !prefs[key] }
    setPrefs(next)
    setSavingPref(key)
    try {
      const res = await api.meMessagePrefs(next)
      setPrefs(res.prefs)
      void api.analyticsTrack('message_pref_change', { pref: key, value: next[key] })
    } catch {
      setPrefs(previous)
    } finally {
      setSavingPref('')
    }
  }

  return (
    <div className="page page--message">
      <SectionHeader title="消息" />
      <div className="message-summary">
        {unread ? `${unread} 条未读` : '全部已读'}
        {messages.length ? ` · 已加载 ${messages.length} 条` : ''}
      </div>

      {loading && !messages.length ? (
        <div className="message-list">
          <Skeleton style={{ height: 92 }} />
          <Skeleton style={{ height: 92 }} />
        </div>
      ) : null}

      {messages.length ? (
        <ul className="message-list">
          {messages.map((message) => (
            <li key={message._id}>
              <button
                type="button"
                className={`message-item ${message.readAt ? '' : 'message-item--unread'}`}
                onClick={() => void openMessage(message)}
              >
                <div className="message-item__head">
                  <span className="message-item__type">{messageTypeLabel(message.type)}</span>
                  <span className="message-item__time">{fromNowText(message.createdAt)}</span>
                </div>
                <div className="message-item__title">{message.title}</div>
                <div className="message-item__content">{message.content}</div>
                {message.readAt ? null : <span className="message-item__dot" aria-label="未读" />}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      {!loading && loaded && !messages.length ? (
        <EmptyView
          icon="✉️"
          title="暂无消息"
          subtitle={MESSAGE_API_READY ? '暂时没有新消息' : '消息 API 接入后会展示真实消息'}
        />
      ) : null}

      {hasMore ? (
        <button
          type="button"
          className="message-more"
          onClick={() => {
            void (async () => {
              if (loading) return
              setLoading(true)
              try {
                const res = await api.meMessages(cursor ? { cursor } : {})
                setMessages((prev) => [...prev, ...res.list])
                const last = res.list[res.list.length - 1]
                if (last) setCursor(last.createdAt)
                setHasMore(res.hasMore)
                setUnread(res.unread)
              } catch {
                /* 分页失败静默，保留已加载内容 */
              } finally {
                setLoading(false)
              }
            })()
          }}
          disabled={loading}
        >
          {loading ? '加载中…' : '加载更多'}
        </button>
      ) : null}

      <section className="section">
        <SectionHeader title="消息偏好" />
        <div className="message-prefs">
          {PREF_ITEMS.map((item) => (
            <label className="message-pref" key={item.key}>
              <span className="message-pref__label">{item.label}</span>
              <input
                type="checkbox"
                className="message-pref__input"
                checked={prefs ? prefs[item.key] : false}
                disabled={!prefs || savingPref === item.key}
                onChange={() => void togglePref(item.key)}
              />
            </label>
          ))}
        </div>
      </section>

      <TabBar badges={{ '/messages': unread }} />
    </div>
  )
}
