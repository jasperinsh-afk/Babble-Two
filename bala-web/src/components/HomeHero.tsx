/**
 * 首页大 Banner：错落堆叠式轮播
 * - 相邻卡片在竖向错位排布（stagger），中心卡片放大、两侧缩小并轻微旋转
 * - 支持鼠标 / 触摸跟手拖拽，松手吸附到最近一张
 * - 点击中心卡片跳 Banner 目标路由，拖动过则不触发跳转
 */
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight } from '@/components/icons'
import { Skeleton, SmartImage } from '@/components/common'
import type { Banner } from '@/types/models'
import { resolveRoute } from '@/utils/config'

const AUTOPLAY_MS = 4600
/** 每张卡片的竖向错位量（px），按索引循环，形成参差节奏 */
const STAGGER_Y = [-16, 18, -6, 26, -20]
/** 相邻卡片水平错位（占卡片自身宽度百分比） */
const STEP_X = 52
/** 拖拽灵敏度：横向划过半屏约等于翻一张 */
const DRAG_FACTOR = 2

interface Props {
  banners: Banner[]
  loading?: boolean
}

/** 环形相对位置：始终落在 [-count/2, count/2)，保证首尾循环 */
function circularRel(index: number, pos: number, count: number) {
  let rel = (index - pos) % count
  if (rel > count / 2) rel -= count
  if (rel < -count / 2) rel += count
  return rel
}

export default function HomeHero({ banners, loading = false }: Props) {
  const navigate = useNavigate()
  const count = banners.length
  const stageRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef({ x: 0, pos: 0, moved: false })
  const [pos, setPos] = useState(0)
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    if (count < 2 || dragging) return
    const timer = window.setInterval(() => setPos((p) => p + 1), AUTOPLAY_MS)
    return () => window.clearInterval(timer)
  }, [count, dragging])

  useEffect(() => {
    setPos(0)
  }, [count])

  function onPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if (count < 2) return
    dragRef.current = { x: event.clientX, pos, moved: false }
    setDragging(true)
  }

  function onPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!dragging) return
    const width = stageRef.current?.clientWidth || 1
    const dx = event.clientX - dragRef.current.x
    if (Math.abs(dx) > 6) dragRef.current.moved = true
    setPos(dragRef.current.pos - (dx / width) * DRAG_FACTOR)
  }

  function endDrag() {
    if (!dragging) return
    setDragging(false)
    setPos((p) => Math.round(p))
  }

  if (loading) {
    return (
      <div className="home-hero home-hero--loading">
        <Skeleton className="home-hero__skeleton" />
      </div>
    )
  }

  if (!count) return null

  const active = ((Math.round(pos) % count) + count) % count

  return (
    <div className={`home-hero ${dragging ? 'is-dragging' : ''}`} aria-roledescription="carousel">
      <div
        className="home-hero__stage"
        ref={stageRef}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onPointerLeave={endDrag}
      >
        {banners.map((banner, index) => {
          const rel = circularRel(index, pos, count)
          const abs = Math.abs(rel)
          const isActive = abs < 0.5
          const style: CSSProperties = {
            transform: `translate3d(calc(-50% + ${rel * STEP_X}%), ${
              STAGGER_Y[index % STAGGER_Y.length] + abs * 12
            }px, 0) rotate(${rel * -4}deg) scale(${1 - Math.min(abs, 2) * 0.13})`,
            zIndex: 30 - Math.round(abs * 10),
            opacity: abs > 1.6 ? 0 : 1,
            pointerEvents: isActive ? 'auto' : 'none',
          }
          return (
            <button
              type="button"
              key={banner._id}
              className={`home-hero__card ${isActive ? 'home-hero__card--active' : ''}`}
              style={style}
              tabIndex={isActive ? 0 : -1}
              aria-hidden={!isActive}
              onClick={() => {
                if (dragRef.current.moved) return
                navigate(resolveRoute(banner.targetRoute))
              }}
            >
              <SmartImage
                className="home-hero__img"
                src={banner.imageUrl}
                alt={banner.title}
                fallback={<span className="home-hero__initial">{(banner.title || '叭').charAt(0)}</span>}
              />
              <span className="home-hero__shade" />
              <span className="home-hero__body">
                <span className="home-hero__tag">{banner.tag || '推荐'}</span>
                <span className="home-hero__title">{banner.title}</span>
                <span className="home-hero__desc">{banner.desc || '戳开看看大家怎么选'}</span>
                <span className="home-hero__cta">去看看 →</span>
              </span>
            </button>
          )
        })}
      </div>

      {count > 1 ? (
        <>
          <button
            type="button"
            className="home-hero__nav home-hero__nav--prev"
            aria-label="上一张"
            onClick={() => setPos((p) => Math.round(p) - 1)}
          >
            <ChevronLeft className="home-hero__nav-icon" />
          </button>
          <button
            type="button"
            className="home-hero__nav home-hero__nav--next"
            aria-label="下一张"
            onClick={() => setPos((p) => Math.round(p) + 1)}
          >
            <ChevronRight className="home-hero__nav-icon" />
          </button>
        </>
      ) : null}

      {count > 1 ? (
        <div className="home-hero__dots" role="tablist" aria-label="Banner 分页">
          {banners.map((banner, index) => (
            <button
              type="button"
              key={banner._id}
              role="tab"
              aria-selected={index === active}
              aria-label={`第 ${index + 1} 张：${banner.title}`}
              className={`home-hero__dot ${index === active ? 'is-active' : ''}`}
              onClick={() => setPos(index)}
            />
          ))}
        </div>
      ) : null}
    </div>
  )
}
