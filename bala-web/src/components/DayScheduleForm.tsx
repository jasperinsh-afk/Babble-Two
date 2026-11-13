import { useEffect, useRef, useState, type FormEvent } from 'react'
import { DayCloseIcon } from '@/components/DayIcons'
import { createScheduleId, isDateKey, type DaySchedule } from '@/utils/days'

interface DayScheduleFormProps {
  open: boolean
  initialDate: string
  onClose: () => void
  onSave: (schedule: DaySchedule) => void
}

export default function DayScheduleForm({ open, initialDate, onClose, onSave }: DayScheduleFormProps) {
  const [title, setTitle] = useState('')
  const [date, setDate] = useState(initialDate)
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const titleRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    setTitle('')
    setDate(initialDate)
    setNote('')
    setError('')
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const focusTimer = window.setTimeout(() => titleRef.current?.focus(), 120)
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.clearTimeout(focusTimer)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [open, initialDate, onClose])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const cleanTitle = title.trim()
    if (!cleanTitle) {
      setError('给这个日子起一个名字吧')
      titleRef.current?.focus()
      return
    }
    if (!isDateKey(date)) {
      setError('请选择有效日期')
      return
    }
    setError('')
    onSave({
      id: createScheduleId(),
      title: cleanTitle,
      date,
      note: note.trim(),
      createdAt: Date.now(),
    })
  }

  if (!open) return null

  return (
    <div className="day-form-mask" onClick={onClose} role="presentation">
      <section
        className="day-form"
        role="dialog"
        aria-modal="true"
        aria-labelledby="day-form-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="day-form__handle" />
        <header className="day-form__header">
          <div><h2 id="day-form-title">添加日子</h2></div>
          <button type="button" className="day-icon-button" aria-label="关闭" onClick={onClose}>
            <DayCloseIcon />
          </button>
        </header>
        <form onSubmit={handleSubmit} noValidate>
          <label className="day-field">
            <span>日程名称</span>
            <input
              ref={titleRef}
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="例如：期末考试、一起旅行"
              maxLength={40}
              autoComplete="off"
            />
          </label>
          <label className="day-field">
            <span>日期</span>
            <input type="date" value={date} onChange={(event) => setDate(event.target.value)} required />
          </label>
          <label className="day-field">
            <span>备注 <small>选填</small></span>
            <textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="写下一句想记住的话"
              maxLength={120}
              rows={3}
            />
            <small className="day-field__count">{note.length}/120</small>
          </label>
          <p className="day-form__error" role="alert">{error}</p>
          <button type="submit" className="btn day-form__submit">保存日子</button>
        </form>
      </section>
    </div>
  )
}
