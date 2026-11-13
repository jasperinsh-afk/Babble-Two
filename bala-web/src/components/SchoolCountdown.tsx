import { useEffect, useState } from 'react'
import { DayClockIcon } from '@/components/DayIcons'
import { getSchoolCountdown } from '@/utils/days'

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

export default function SchoolCountdown() {
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const countdown = getSchoolCountdown(now)
  const units = [
    ...(countdown.days > 0 ? [{ value: countdown.days, label: '天', padded: false }] : []),
    { value: countdown.hours, label: '时', padded: true },
    { value: countdown.minutes, label: '分', padded: true },
    { value: countdown.seconds, label: '秒', padded: true },
  ]

  return (
    <section className={`school-countdown school-countdown--${countdown.mode}`} aria-label={countdown.title}>
      <div className="school-countdown__heading">
        <span className="school-countdown__label">
          <DayClockIcon className="school-countdown__icon" />
          {countdown.title}
        </span>
        <span className="school-countdown__subtitle">{countdown.subtitle}</span>
      </div>
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
        <span>放学 15:20</span>
      </div>
    </section>
  )
}
