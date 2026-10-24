import type { VoteResults } from '@/types/models'

/** 投票结果图表（对应 components/result-chart，含 PK 双配色模式） */
export function ResultChart({
  results,
  pollType = 'single',
}: {
  results: VoteResults | null
  pollType?: string
}) {
  const rows = results?.options ?? []
  const total = results?.total || 0
  const isPk = pollType === 'pk' && rows.length === 2

  const percentOf = (count?: number) => (total ? Math.round(((count || 0) / total) * 1000) / 10 : 0)
  const leftPercent = isPk ? percentOf(rows[0]?.count) : 0
  const rightPercent = isPk ? percentOf(rows[1]?.count) : 0

  return (
    <div className="result-chart">
      <div className="result-chart__header">
        <div className="result-chart__total">
          <span className="result-chart__total-num">{total}</span>
          <span className="result-chart__total-label">人参与</span>
        </div>
        {isPk ? (
          <div className="result-chart__pk">
            <div className="result-chart__pk-item result-chart__pk-left">
              <span className="result-chart__pk-num">{leftPercent}%</span>
              <span className="result-chart__pk-label">{rows[0]?.label}</span>
            </div>
            <span className="result-chart__pk-vs">VS</span>
            <div className="result-chart__pk-item result-chart__pk-right">
              <span className="result-chart__pk-num">{rightPercent}%</span>
              <span className="result-chart__pk-label">{rows[1]?.label}</span>
            </div>
          </div>
        ) : null}
      </div>

      {!isPk ? (
        <div className="result-chart__list">
          {rows.map((row) => (
            <div className="result-chart__row" key={row.optionId}>
              <div className="result-chart__info">
                <span className="result-chart__label">{row.label}</span>
                <span className="result-chart__value">{row.count || 0} 票</span>
              </div>
              <div className="result-chart__bar-bg">
                <div className="result-chart__bar-fill" style={{ width: `${row.percent || 0}%` }} />
              </div>
              <span className="result-chart__percent">{row.percent || 0}%</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="result-chart__list">
          <div className="result-chart__pk-bar">
            <div
              className="result-chart__pk-fill result-chart__pk-fill--left"
              style={{ width: `${leftPercent}%` }}
            />
            <div
              className="result-chart__pk-fill result-chart__pk-fill--right"
              style={{ width: `${rightPercent}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
