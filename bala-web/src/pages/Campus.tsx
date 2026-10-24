import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import CalendarContent from '@/components/content/CalendarContent'
import ClubContent from '@/components/content/ClubContent'
import LivingContent from '@/components/content/LivingContent'
import VoteContent from '@/components/content/VoteContent'
import { TabBar } from '@/components/chrome'

const SEGMENTS = [
  { key: 'event', label: '活动' },
  { key: 'vote', label: '投票' },
  { key: 'club', label: '社团' },
  { key: 'service', label: '服务' },
]

function initialSegment(searchParams: URLSearchParams) {
  const tab = searchParams.get('tab')
  if (tab && SEGMENTS.some((segment) => segment.key === tab)) return tab
  if (searchParams.get('eventId')) return 'event'
  return 'event'
}

export default function Campus() {
  const [searchParams] = useSearchParams()
  const [current, setCurrent] = useState(() => initialSegment(searchParams))

  return (
    <div className="page page--campus">
      <div className="campus-segment" role="tablist" aria-label="校园内容分段">
        {SEGMENTS.map((segment) => (
          <button
            type="button"
            role="tab"
            aria-selected={current === segment.key}
            key={segment.key}
            className={`campus-segment__item ${
              current === segment.key ? 'campus-segment__item--active' : ''
            }`}
            onClick={() => setCurrent(segment.key)}
          >
            {segment.label}
          </button>
        ))}
      </div>

      {current === 'event' ? <CalendarContent embedded /> : null}
      {current === 'vote' ? <VoteContent embedded /> : null}
      {current === 'club' ? <ClubContent embedded /> : null}
      {current === 'service' ? <LivingContent embedded /> : null}

      <TabBar />
    </div>
  )
}
