/** 轻量全局反馈：toast 与 loading 遮罩（对应小程序 wx.showToast / wx.showLoading） */
import { useEffect, useState } from 'react'

export interface ToastItem {
  id: number
  text: string
}

type Listener<T> = (value: T) => void

let toastId = 0
let toasts: ToastItem[] = []
const toastListeners = new Set<Listener<ToastItem[]>>()

export function toast(text: string, duration = 2200) {
  if (!text) return
  const item = { id: ++toastId, text }
  toasts = [...toasts.slice(-2), item]
  toastListeners.forEach((fn) => fn(toasts))
  window.setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== item.id)
    toastListeners.forEach((fn) => fn(toasts))
  }, duration)
}

export function useToasts(): ToastItem[] {
  const [items, setItems] = useState(toasts)
  useEffect(() => {
    toastListeners.add(setItems)
    return () => {
      toastListeners.delete(setItems)
    }
  }, [])
  return items
}

let loadingCount = 0
let loadingText = ''
const loadingListeners = new Set<Listener<{ visible: boolean; text: string }>>()

function emitLoading() {
  const value = { visible: loadingCount > 0, text: loadingText }
  loadingListeners.forEach((fn) => fn(value))
}

export function showLoading(text = '加载中…') {
  loadingCount += 1
  loadingText = text
  emitLoading()
}

export function hideLoading() {
  loadingCount = Math.max(0, loadingCount - 1)
  if (loadingCount === 0) loadingText = ''
  emitLoading()
}

export function useLoading() {
  const [state, setState] = useState({ visible: false, text: '' })
  useEffect(() => {
    loadingListeners.add(setState)
    return () => {
      loadingListeners.delete(setState)
    }
  }, [])
  return state
}
