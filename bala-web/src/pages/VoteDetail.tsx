import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { ResultChart } from '@/components/ResultChart'
import { EmptyView, SectionHeader, Skeleton } from '@/components/common'
import { TopBar } from '@/components/chrome'
import { pollTagLabel, pollTypeLabel } from '@/utils/config'
import { countdownText } from '@/utils/format'
import { toast } from '@/utils/feedback'

export default function VoteDetail() {
  const { pollId = '' } = useParams()
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<string[]>([])
  const [showResults, setShowResults] = useState(false)
  const [initialized, setInitialized] = useState(false)

  const { data: poll, isLoading } = useQuery({
    queryKey: ['vote', 'detail', pollId],
    queryFn: () => api.voteDetail(pollId),
    enabled: Boolean(pollId),
  })

  const { data: results } = useQuery({
    queryKey: ['vote', 'results', pollId],
    queryFn: () => api.voteResults(pollId, { silent: true }),
    enabled: Boolean(pollId) && showResults,
  })

  useEffect(() => {
    if (!poll || initialized) return
    setSelected(poll.myChoice || [])
    setShowResults(poll.pollType !== 'groupbuy' && Boolean(poll.hasVoted))
    setInitialized(true)
  }, [poll, initialized])

  const isChain = poll?.pollType === 'groupbuy'
  const isSingleLike = poll ? ['single', 'pk', 'groupbuy'].includes(poll.pollType) : true
  const ended = poll?.endAt ? new Date(poll.endAt).getTime() < Date.now() : false
  const closed = Boolean(ended) || poll?.status === 'closed'
  const minChoices = poll?.pollType === 'ranking' ? 2 : 1

  const canSubmit = useMemo(() => {
    if (!poll || isChain || closed) return false
    if (selected.length < minChoices) return false
    if (poll.hasVoted && !poll.canChange) return false
    return true
  }, [poll, isChain, closed, selected.length, minChoices])

  const chainPercent =
    isChain && poll?.maxParticipants
      ? Math.min(100, Math.round(((poll.participantCount || 0) / poll.maxParticipants) * 100))
      : 0

  async function refresh() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['vote', 'detail', pollId] }),
      queryClient.invalidateQueries({ queryKey: ['vote', 'results', pollId] }),
      queryClient.invalidateQueries({ queryKey: ['vote', 'list'] }),
      queryClient.invalidateQueries({ queryKey: ['home', 'feed'] }),
      queryClient.invalidateQueries({ queryKey: ['me', 'overview'] }),
    ])
  }

  const castMutation = useMutation({
    mutationFn: () => api.voteCast(pollId, selected),
    onSuccess: async () => {
      toast('投票成功')
      setShowResults(true)
      await refresh()
    },
  })

  const chainMutation = useMutation<unknown, Error, 'join' | 'leave'>({
    mutationFn: (action: 'join' | 'leave') =>
      action === 'join' ? api.joinChain(pollId, selected[0]) : api.leaveChain(pollId),
    onSuccess: async (_, action) => {
      toast(action === 'join' ? '接龙成功' : '已取消')
      await refresh()
    },
  })

  function toggleOption(optionId: string) {
    if (!poll || closed) return
    if (poll.hasVoted && !poll.canChange && !isChain) return
    if (isChain && poll.joined) return

    if (isSingleLike) {
      setSelected([optionId])
      return
    }
    setSelected((prev) => {
      if (prev.includes(optionId)) return prev.filter((id) => id !== optionId)
      if (poll.maxChoices && prev.length >= poll.maxChoices) {
        toast(`最多选 ${poll.maxChoices} 项`)
        return prev
      }
      return [...prev, optionId]
    })
  }

  const submitting = castMutation.isPending || chainMutation.isPending

  return (
    <div className="page page--vote-detail page--with-topbar">
      <TopBar back />
      {isLoading || !poll ? (
        <div className="section">
          <Skeleton style={{ height: 150, marginBottom: 16 }} />
          <Skeleton style={{ height: 260 }} />
          {!isLoading && !poll ? (
            <EmptyView icon="🗳️" title="投票不存在或已下架" subtitle="返回列表看看其他投票" />
          ) : null}
        </div>
      ) : (
        <>
          <div className="vote-detail__header card section fade-up">
            <div className="vote-detail__tags">
              <span className="chip">{pollTypeLabel[poll.pollType] || '投票'}</span>
              {poll.tag ? <span className="chip">{pollTagLabel[poll.tag] || poll.tag}</span> : null}
              <span className="vote-detail__time">
                {poll.endAt ? `截止 ${countdownText(poll.endAt)}` : ''}
              </span>
            </div>
            <h1 className="vote-detail__title">{poll.title}</h1>
            {poll.description ? <p className="vote-detail__desc">{poll.description}</p> : null}
            <div className="vote-detail__count">{poll.totalVotes || 0} 人已参与</div>
          </div>

          {!showResults || isChain ? (
            <div className="vote-detail__options card section">
              {poll.options.map((option) => {
                const active = selected.includes(option.optionId)
                const rank = selected.indexOf(option.optionId)
                return (
                  <div
                    key={option.optionId}
                    className={`vote-option ${active ? 'vote-option--selected' : ''}`}
                    onClick={() => toggleOption(option.optionId)}
                    role="checkbox"
                    aria-checked={active}
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && toggleOption(option.optionId)}
                  >
                    <span className="vote-option__check">
                      {isSingleLike ? (
                        <span className="vote-option__circle" />
                      ) : (
                        <span className="vote-option__square" />
                      )}
                    </span>
                    <span className="vote-option__body">
                      <span className="vote-option__label">{option.label}</span>
                      {isChain ? (
                        <span className="vote-option__count">{option.count || 0} 人已接龙</span>
                      ) : null}
                      {poll.pollType === 'ranking' && active ? (
                        <span className="vote-option__count">优先级第 {rank + 1} 位</span>
                      ) : null}
                    </span>
                  </div>
                )
              })}
              {poll.pollType === 'ranking' ? (
                <p className="vote-detail__hint">按期待程度依次点选，至少选择 2 项</p>
              ) : null}
              {poll.pollType === 'multi' && poll.maxChoices ? (
                <p className="vote-detail__hint">
                  最多可选 {poll.maxChoices} 项，已选 {selected.length} 项
                </p>
              ) : null}
            </div>
          ) : null}

          {showResults && !isChain ? (
            <section className="section fade-up">
              <SectionHeader title="结果" />
              <ResultChart results={results ?? null} pollType={poll.pollType} />
            </section>
          ) : null}

          {isChain ? (
            <div className="vote-detail__chain card section">
              <div className="vote-detail__chain-title">接龙进度</div>
              <div className="vote-detail__chain-bar">
                <div className="vote-detail__chain-fill" style={{ width: `${chainPercent}%` }} />
              </div>
              <div className="vote-detail__chain-text">
                {poll.participantCount || 0} / {poll.maxParticipants || '∞'} 人
                {poll.isFull ? <span className="vote-detail__chain-full">已满员</span> : null}
              </div>
              {poll.joined ? (
                <button
                  type="button"
                  className="btn btn--ghost"
                  disabled={submitting}
                  onClick={() => chainMutation.mutate('leave')}
                >
                  取消接龙
                </button>
              ) : (
                <button
                  type="button"
                  className="btn"
                  disabled={submitting || !selected.length || closed || poll.isFull}
                  onClick={() => chainMutation.mutate('join')}
                >
                  {poll.isFull ? '已满员' : '我要接龙'}
                </button>
              )}
            </div>
          ) : null}

          {poll.hasVoted && !showResults && !isChain ? (
            <div className="vote-detail__voted-tip">你已参与，可修改选择后重新提交</div>
          ) : null}

          {!isChain ? (
            <div className="action-dock">
              {showResults ? (
                poll.canChange && !closed ? (
                  <button type="button" className="btn btn--ghost" onClick={() => setShowResults(false)}>
                    修改我的投票
                  </button>
                ) : (
                  <button type="button" className="btn" onClick={() => setShowResults(false)}>
                    查看选项
                  </button>
                )
              ) : (
                <button
                  type="button"
                  className="btn"
                  disabled={!canSubmit || submitting}
                  onClick={() => {
                    if (!selected.length) {
                      toast('请选择选项')
                      return
                    }
                    castMutation.mutate()
                  }}
                >
                  {closed ? '投票已结束' : poll.hasVoted ? '修改投票' : '投 票'}
                </button>
              )}
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}
