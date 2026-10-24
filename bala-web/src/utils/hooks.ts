import { useEffect, useRef } from 'react'

/** 滚动到底自动加载（对应小程序 onReachBottom） */
export function useInfiniteScroll(onReachBottom: () => void, enabled = true) {
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const callbackRef = useRef(onReachBottom)
  callbackRef.current = onReachBottom

  useEffect(() => {
    const node = sentinelRef.current
    if (!node || !enabled) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) callbackRef.current()
      },
      { rootMargin: '240px 0px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [enabled])

  return sentinelRef
}
