import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { api } from '@/api/endpoints'
import {
  DayBackIcon,
  DayCalendarIcon,
  DayDownloadIcon,
  DayShareIcon,
  DayTrashIcon,
} from '@/components/DayIcons'
import { toast } from '@/utils/feedback'
import {
  copyText,
  createScheduleImage,
  downloadScheduleImage,
  scheduleImageName,
  scheduleShareUrl,
} from '@/utils/dayShare'
import {
  dayDifference,
  formatDayDate,
  isDateKey,
  readSchedules,
  writeSchedules,
  type DaySchedule,
} from '@/utils/days'

export default function DayDetail() {
  const navigate = useNavigate()
  const { scheduleId = '' } = useParams()
  const [searchParams] = useSearchParams()
  const [schedules, setSchedules] = useState<DaySchedule[]>(() => readSchedules())
  const [now, setNow] = useState(() => new Date())
  const [busy, setBusy] = useState<'share' | 'image' | null>(null)
  const [shareImageUrl, setShareImageUrl] = useState('')
  const isShared = scheduleId === 'share'

  const schedule = useMemo<DaySchedule | null>(() => {
    if (isShared) {
      const title = searchParams.get('title')?.trim().slice(0, 40) || ''
      const date = searchParams.get('date') || ''
      if (!title || !isDateKey(date)) return null
      return {
        id: 'shared',
        title,
        date,
        note: (searchParams.get('note') || '').trim().slice(0, 120),
        createdAt: 0,
      }
    }
    return schedules.find((item) => item.id === scheduleId) || null
  }, [isShared, scheduleId, schedules, searchParams])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => () => {
    if (shareImageUrl) URL.revokeObjectURL(shareImageUrl)
  }, [shareImageUrl])

  async function saveImage() {
    if (!schedule || busy) return
    setBusy('image')
    try {
      const url = await downloadScheduleImage(schedule)
      setShareImageUrl(url)
      toast('图片已生成，若未自动下载可长按或右键保存')
    } catch (error) {
      toast(error instanceof Error ? error.message : '图片保存失败，请重试')
    } finally {
      setBusy(null)
    }
  }

  async function shareSchedule() {
    if (!schedule || busy) return
    setBusy('share')
    const url = scheduleShareUrl(schedule)
    try {
      if (typeof navigator.share === 'function') {
        const blob = await createScheduleImage(schedule)
        const file = new File([blob], scheduleImageName(schedule), { type: 'image/png' })
        if (typeof navigator.canShare === 'function' && navigator.canShare({ files: [file] })) {
          await navigator.share({ title: schedule.title, text: formatDayDate(schedule.date), files: [file] })
        } else {
          await navigator.share({ title: schedule.title, text: formatDayDate(schedule.date), url })
        }
        toast('分享成功')
      } else if (await copyText(url)) {
        toast('分享链接已复制')
      } else {
        toast('复制失败，请使用保存图片后分享')
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      if (await copyText(url)) toast('分享链接已复制')
      else toast('暂时无法分享，请保存图片后分享')
    } finally {
      setBusy(null)
    }
  }

  function deleteSchedule() {
    if (!schedule || isShared || !window.confirm(`删除“${schedule.title}”吗？`)) return
    const next = schedules.filter((item) => item.id !== schedule.id)
    try {
      writeSchedules(next)
      setSchedules(next)
      void api.daysRemove(schedule.id).catch(() => {})
      toast('日程已删除')
      navigate('/days', { replace: true })
    } catch {
      toast('删除失败，请检查浏览器存储权限')
    }
  }

  return (
    <div className="page page--plain day-detail">
      <header className="day-detail__topbar">
        <button type="button" aria-label="返回日子" onClick={() => navigate('/days')}>
          <DayBackIcon />
        </button>
        <strong>日子分享</strong>
        <span />
      </header>

      {schedule ? (
        <main className="day-detail__main">
          <article className="day-share-card">
            <div className="day-share-card__brand"><img src="/assets/brand/logo-mark.png" alt="叭啦" /><span>叭啦·过日子</span></div>
            <time className="day-share-card__date" dateTime={schedule.date}>
              {formatDayDate(schedule.date)}
            </time>
            <h1>{schedule.title}</h1>
            <div className="day-share-card__count">
              <span>{dayDifference(schedule.date, now) === 0 ? '就是今天' : dayDifference(schedule.date, now) > 0 ? '还有' : '已经'}</span>
              <div>
                <strong>{Math.abs(dayDifference(schedule.date, now))}</strong>
                <small>天</small>
              </div>
            </div>
            {schedule.note ? <p className="day-share-card__note">{schedule.note}</p> : null}
          </article>
          <div className="day-detail__actions">
            <button type="button" className="day-detail__action day-detail__action--secondary" onClick={saveImage} disabled={Boolean(busy)}>
              <DayDownloadIcon />
              {busy === 'image' ? '正在生成…' : '保存图片'}
            </button>
            <button type="button" className="day-detail__action" onClick={shareSchedule} disabled={Boolean(busy)}>
              <DayShareIcon />
              {busy === 'share' ? '正在准备…' : '分享日子'}
            </button>
          </div>
          {shareImageUrl ? (
            <div className="day-share-preview">
              <img src={shareImageUrl} alt={`${schedule.title}分享图`} />
              <p>若未自动下载，请长按或右键图片保存</p>
            </div>
          ) : null}
          {!isShared ? (
            <button type="button" className="day-detail__delete" onClick={deleteSchedule}>
              <DayTrashIcon /> 删除这个日程
            </button>
          ) : null}
        </main>
      ) : (
        <main className="day-detail__missing">
          <DayCalendarIcon />
          <h1>没有找到这个日子</h1>
          <p>{isShared ? '分享链接不完整，请向朋友重新获取' : '它可能已被删除，或保存在另一台设备上'}</p>
          <button type="button" className="btn" onClick={() => navigate('/days')}>返回我的日子</button>
        </main>
      )}
    </div>
  )
}
