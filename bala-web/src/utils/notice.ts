/** 「校区尚未开通该服务」底部弹层的极简全局状态（与 toast 同款订阅模式） */
import { useEffect, useState } from 'react'

type Listener = (value: string | null) => void

let current: string | null = null
const listeners = new Set<Listener>()

function emit() {
  listeners.forEach((fn) => fn(current))
}

/** serviceKey 见 components/services 中的 CAMPUS_SERVICES */
export function showServiceNotice(serviceKey: string) {
  current = serviceKey
  emit()
}

export function closeServiceNotice() {
  if (!current) return
  current = null
  emit()
}

export function useServiceNotice(): string | null {
  const [value, setValue] = useState(current)
  useEffect(() => {
    listeners.add(setValue)
    return () => {
      listeners.delete(setValue)
    }
  }, [])
  return value
}
