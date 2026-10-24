/** 统一 API 封装（对应小程序 utils/api.js：loading / toast / dedupe / 重试一次） */
import axios from 'axios'
import { hideLoading, showLoading, toast } from '@/utils/feedback'
import { ensureSession } from '@/utils/identity'
import type { ApiEnvelope } from '@/types/models'

export class ApiError extends Error {
  code: string
  business: boolean
  status?: number

  constructor(message: string, code = '', business = true, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.business = business
    this.status = status
  }
}

export interface CallOptions {
  /** 静默：失败不弹 toast（用于首屏预取、后台刷新） */
  silent?: boolean
  /** 传入文案则显示全屏 loading，例如 '提交中…' */
  loading?: string
  /** 网络错误不自动重试（业务错误本就永重试） */
  noRetry?: boolean
}

const http = axios.create({ baseURL: '/api/v1/web', timeout: 25000 })
const inflight = new Map<string, Promise<unknown>>()

async function request<T>(
  fn: string,
  action: string,
  payload: Record<string, unknown>,
  allowRetry: boolean,
): Promise<T> {
  const session = await ensureSession()
  const headers = {
    'X-Bala-Identity': session.identity,
    'X-Bala-Token': session.token,
  }

  try {
    const resp = await http.post<ApiEnvelope<T>>(`/${fn}/${action}`, payload, { headers })
    const body = resp.data
    if (!body || body.ok === false) {
      throw new ApiError(body?.message || '服务异常', body?.code || '')
    }
    return body.data as T
  } catch (error) {
    if (error instanceof ApiError) throw error

    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      const body = error.response?.data as ApiEnvelope<T> | undefined

      // 身份失效：重新签发后重放一次
      if (status === 401) {
        await ensureSession(true)
        if (allowRetry) return request<T>(fn, action, payload, false)
      }
      if (body && body.ok === false) {
        throw new ApiError(body.message || '服务异常', body.code || '', true, status)
      }
      if (!error.response && allowRetry) {
        // 网络错误自动重试一次
        return request<T>(fn, action, payload, false)
      }
      throw new ApiError(
        error.response ? `服务异常（${status}）` : '网络连接失败，请稍后重试',
        body?.code || '',
        false,
        status,
      )
    }
    throw error
  }
}

export async function call<T = unknown>(
  fn: string,
  action: string,
  payload: Record<string, unknown> = {},
  options: CallOptions = {},
): Promise<T> {
  const key = `${fn}.${action}:${JSON.stringify(payload)}`
  const existing = inflight.get(key)
  if (existing) return existing as Promise<T>

  const task = (async () => {
    if (options.loading) showLoading(options.loading)
    try {
      return await request<T>(fn, action, payload, !options.noRetry)
    } catch (error) {
      const message = error instanceof Error ? error.message : '服务异常'
      if (!options.silent) toast(message)
      throw error
    } finally {
      if (options.loading) hideLoading()
    }
  })()

  inflight.set(key, task)
  try {
    return await task
  } finally {
    inflight.delete(key)
  }
}
