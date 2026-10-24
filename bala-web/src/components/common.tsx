import { useEffect, useState, type CSSProperties, type ReactNode } from 'react'

/** 区块标题 + 右侧动作（对应 components/section-header） */
export function SectionHeader({
  title,
  actionText,
  onAction,
}: {
  title: string
  actionText?: string
  onAction?: () => void
}) {
  return (
    <div className="section-header">
      <div className="section-header__title">
        <img className="section-header__spark" src="/assets/brand/spark.png" alt="" />
        <span>{title}</span>
      </div>
      {actionText ? (
        <button type="button" className="section-header__action" onClick={onAction}>
          {actionText}
        </button>
      ) : null}
    </div>
  )
}

/** 空态占位（对应 components/empty-view） */
export function EmptyView({
  icon = '📭',
  title = '暂无内容',
  subtitle = '',
  actionText = '',
  onAction,
}: {
  icon?: string
  title?: string
  subtitle?: string
  actionText?: string
  onAction?: () => void
}) {
  return (
    <div className="empty-view">
      <div className="empty-view__icon">{icon}</div>
      <div className="empty-view__title">{title}</div>
      {subtitle ? <div className="empty-view__subtitle">{subtitle}</div> : null}
      {actionText ? (
        <button type="button" className="empty-view__action" onClick={onAction}>
          {actionText}
        </button>
      ) : null}
    </div>
  )
}

/** 图片加载失败时回退为首字占位（小程序无图分支的网页等价实现） */
export function SmartImage({
  src,
  alt = '',
  className = '',
  fallback,
  style,
}: {
  src?: string | null
  alt?: string
  className?: string
  fallback?: ReactNode
  style?: CSSProperties
}) {
  const [failed, setFailed] = useState(false)
  useEffect(() => setFailed(false), [src])

  if (!src || failed) {
    return (
      <div className={`${className} image-fallback`} style={style} aria-label={alt}>
        {fallback ?? <span>{(alt || '叭').charAt(0)}</span>}
      </div>
    )
  }
  return (
    <img
      className={className}
      style={style}
      src={src}
      alt={alt}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}

export function Skeleton({ className = '', style }: { className?: string; style?: CSSProperties }) {
  return <div className={`skeleton ${className}`} style={style} aria-hidden="true" />
}

/** 居中确认弹窗（对应 wx.showModal） */
export function Modal({
  open,
  title,
  children,
  confirmText = '确定',
  cancelText = '取消',
  showCancel = true,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  children?: ReactNode
  confirmText?: string
  cancelText?: string
  showCancel?: boolean
  onConfirm?: () => void
  onCancel?: () => void
}) {
  if (!open) return null
  return (
    <div className="modal-mask" onClick={onCancel} role="presentation">
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal__title">{title}</div>
        <div className="modal__body">{children}</div>
        <div className="modal__actions">
          {showCancel ? (
            <button type="button" className="btn btn--ghost" onClick={onCancel}>
              {cancelText}
            </button>
          ) : null}
          <button type="button" className="btn" onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
