/** 「校区尚未开通该服务」底部弹层 —— 扫码与「生活」板块的统一占位反馈 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LockIcon } from '@/components/icons'
import { findService } from '@/components/services'
import { closeServiceNotice, useServiceNotice } from '@/utils/notice'

export function ServiceNoticeHost() {
  const serviceKey = useServiceNotice()
  const navigate = useNavigate()

  useEffect(() => {
    if (!serviceKey) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeServiceNotice()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [serviceKey])

  if (!serviceKey) return null

  const service = findService(serviceKey)

  return (
    <div className="notice-mask" onClick={closeServiceNotice} role="presentation">
      <div
        className="notice-sheet pop-in"
        role="dialog"
        aria-modal="true"
        aria-label="校区尚未开通该服务"
        onClick={(e) => e.stopPropagation()}
      >
        <span className="notice-sheet__handle" />
        <div className="notice-sheet__icon">
          <LockIcon className="notice-sheet__icon-svg" />
        </div>
        <div className="notice-sheet__title">校区尚未开通该服务</div>
        <div className="notice-sheet__text">
          {service ? (
            <>
              「{service.label}」{service.desc}，暂未在你所在的校区开通。
            </>
          ) : (
            '该服务暂未在你所在的校区开通。'
          )}
          <br />
          开通后会第一时间在这里通知你。
        </div>
        <div className="notice-sheet__actions">
          <button type="button" className="btn btn--ghost" onClick={closeServiceNotice}>
            知道了
          </button>
          <button type="button" className="btn" onClick={() => {
            closeServiceNotice()
            navigate('/vote')
          }}>
            去看投票
          </button>
        </div>
      </div>
    </div>
  )
}
