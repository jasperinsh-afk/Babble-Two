/** 网页端匿名身份（对应小程序 utils/identity.js 的 ensureOpenid） */
import type { Session } from '@/types/models'

const KEY_IDENTITY = 'bala_identity'
const KEY_TOKEN = 'bala_token'

let cached: Session | null = null
let pending: Promise<Session> | null = null

export function getSession(): Session | null {
  if (cached) return cached
  try {
    const identity = localStorage.getItem(KEY_IDENTITY)
    const token = localStorage.getItem(KEY_TOKEN)
    if (identity && token) {
      cached = { identity, token }
      return cached
    }
  } catch {
    /* localStorage 不可用（隐私模式）时退化为内存会话 */
  }
  return null
}

function saveSession(session: Session) {
  cached = session
  try {
    localStorage.setItem(KEY_IDENTITY, session.identity)
    localStorage.setItem(KEY_TOKEN, session.token)
  } catch {
    /* 忽略持久化失败 */
  }
}

async function requestSession(): Promise<Session> {
  const resp = await fetch('/api/v1/web/session', { method: 'POST' })
  if (!resp.ok) throw new Error('身份签发失败，请检查后端是否已启动')
  const body = await resp.json()
  if (!body.ok || !body.data) throw new Error(body.message || '身份签发失败')
  const session = body.data as Session
  saveSession(session)
  return session
}

/** 获取或签发身份；并发调用共享同一次请求 */
export async function ensureSession(force = false): Promise<Session> {
  if (!force) {
    const existing = getSession()
    if (existing) return existing
    if (pending) return pending
  }
  pending = requestSession().finally(() => {
    pending = null
  })
  return pending
}

export function clearSession() {
  cached = null
  try {
    localStorage.removeItem(KEY_IDENTITY)
    localStorage.removeItem(KEY_TOKEN)
  } catch {
    /* ignore */
  }
}

/** 网页端与小程序账号的绑定状态（openid 已由服务端脱敏） */
export interface LinkState {
  bound: boolean
  openid: string
  mode: 'cloud' | 'local'
}

/** 绑定接口走独立路由 /session/*，不是 /{fn}/{action} 通用转发，因此单独封装 */
async function sessionRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = await ensureSession()
  const resp = await fetch(`/api/v1/web${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-Bala-Identity': session.identity,
      'X-Bala-Token': session.token,
    },
  })
  const body = await resp.json()
  if (!body || body.ok === false) {
    throw new Error(body?.message || '请求失败，请稍后重试')
  }
  return body.data as T
}

export function fetchLinkStatus(): Promise<LinkState> {
  return sessionRequest<LinkState>('/session/link')
}

export function bindAccount(code: string): Promise<{ bound: boolean; openid: string }> {
  return sessionRequest('/session/bind', {
    method: 'POST',
    body: JSON.stringify({ code }),
  })
}

export function unbindAccount(): Promise<{ bound: boolean }> {
  return sessionRequest('/session/link', { method: 'DELETE' })
}
