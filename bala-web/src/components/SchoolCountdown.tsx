import { useEffect, useState } from 'react'
import { DayClockIcon } from '@/components/DayIcons'
import { getSchoolCountdown, readSchoolMode, writeSchoolMode, SCHOOL_MODES } from '@/utils/days'

type SchoolMode = keyof typeof SCHOOL_MODES

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

const MODE_KEYS: SchoolMode[] = ['normal', 'bus', 'study']
const MODE_DESC: Record<SchoolMode, string> = {
  normal: '按常规作息放学',
  bus: '等延时校车时使用',
  study: '上晚自习时使用',
}

export default function SchoolCountdown() {
  const [now, setNow] = useState(() => new Date())
  const [mode, setMode] = useState<SchoolMode>(() => readSchoolMode())
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const countdown = getSchoolCountdown(now, mode)
  const units = [
    ...(countdown.days > 0 ? [{ value: countdown.days, label: '天', padded: false }] : []),
    { value: countdown.hours, label: '时', padded: true },
    { value: countdown.minutes, label: '分', padded: true },
    { value: countdown.seconds, label: '秒', padded: true },
  ]

  const choose = (next: SchoolMode) => {
    writeSchoolMode(next)
    setMode(next)
    setOpen(false)
  }

  return (
    <section className={`school-countdown school-countdown--${countdown.mode}`} aria-label={countdown.title}>
      <div className="school-countdown__heading">
        <span className="school-countdown__label">
          <DayClockIcon className="school-countdown__icon" />
          {countdown.title}
        </span>
        <button
          type="button"
          className="school-mode-picker__trigger"
          disabled={!countdown.selectable}
          aria-expanded={open}
          onClick={() => setOpen(value => !value)}
        >
          {countdown.label}{countdown.selectable ? ' ▾' : ''}
        </button>
      </div>
      <div className="school-countdown__subtitle">{countdown.subtitle}</div>
      {open && countdown.selectable ? (
        <div className="school-mode-picker__menu">
          {MODE_KEYS.map((key) => (
            <button
              type="button"
              key={key}
              className={`school-mode-picker__option${key === mode ? ' school-mode-picker__option--active' : ''}`}
              onClick={() => choose(key)}
            >
              <span className="school-mode-picker__name">{SCHOOL_MODES[key].label}</span>
              <span className="school-mode-picker__desc">{MODE_DESC[key]}</span>
              <span className="school-mode-picker__time">{SCHOOL_MODES[key].time}</span>
            </button>
          ))}
        </div>
      ) : null}
      <time className="school-countdown__time" dateTime={countdown.target.toISOString()}>
        {units.map((unit, index) => (
          <span className="school-countdown__unit-wrap" key={unit.label}>
            {index > 0 ? <span className="school-countdown__colon">:</span> : null}
            <span className="school-countdown__unit">
              <strong>{unit.padded ? pad(unit.value) : unit.value}</strong>
              <small>{unit.label}</small>
            </span>
          </span>
        ))}
      </time>
      <div className="school-countdown__footer">
        <span>上学 08:05</span>
        <span className="school-countdown__line" />
        <span>放学 {countdown.endText}</span>
      </div>
      {!countdown.selectable ? (
        <div className="school-countdown__notice">周五自动切换单一模式：14:40 放学，过点后倒计时到周一上学</div>
      ) : null}
    </section>
  )
}
