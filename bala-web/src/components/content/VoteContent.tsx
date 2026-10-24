import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { PollCard } from '@/components/cards'
import { EmptyView, Skeleton } from '@/components/common'
import { TabBar } from '@/components/chrome'
import { useInfiniteScroll } from '@/utils/hooks'

const TABS = [
  { tag: 'all', label: '全部' },
  { tag: 'news', label: '时事' },
  { tag: 'campus', label: '学习' },
  { tag: 'meme', label: '热梗' },
  { tag: 'group', label: '接龙' },
]

export default function VoteContent({ embedded = false }: { embedded?: boolean }) {
  const [tag, setTag] = useState('all')
  const navigate = useNavigate()

  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ['vote', 'list', tag],
    queryFn: ({ pageParam }) => api.voteList(tag, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => (lastPage.hasMore ? pages.length : undefined),
  })

  const polls = data?.pages.flatMap((page) => page.list) ?? []
  const sentinelRef = useInfiniteScroll(
    () => {
      if (hasNextPage && !isFetchingNextPage) void fetchNextPage()
    },
    Boolean(hasNextPage),
  )

  return (
    <div className={`${embedded ? '' : 'page'} page--vote-list`}>
      <div className="vote-tabs">
        <div className="vote-tabs__scroll">
          <div className="vote-tabs__wrap">
            {TABS.map((tab) => (
              <button
                type="button"
                key={tab.tag}
                className={`vote-tabs__item ${tag === tab.tag ? 'vote-tabs__item--active' : ''}`}
                onClick={() => setTag(tab.tag)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="vote-list">
        {isLoading
          ? [0, 1, 2].map((i) => <Skeleton key={i} style={{ height: 118, marginBottom: 10 }} />)
          : polls.map((poll) => (
              <PollCard key={poll._id} poll={poll} onClick={() => navigate(`/vote/${poll._id}`)} />
            ))}
        {isFetchingNextPage ? <Skeleton style={{ height: 118 }} /> : null}
      </div>

      {!isLoading && !polls.length ? (
        <EmptyView icon="🗳️" title="暂无投票" subtitle="切换标签看看，精彩内容马上就来" />
      ) : null}

      <div ref={sentinelRef} />
      {!hasNextPage && polls.length ? <div className="vote-list__footer">— 已经到底啦 —</div> : null}
      {embedded ? null : <TabBar />}
    </div>
  )
}
