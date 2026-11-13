import { useNavigate } from 'react-router-dom'
import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { PollCard } from '@/components/cards'
import { EmptyView, Skeleton } from '@/components/common'
import { TabBar } from '@/components/chrome'
import { useInfiniteScroll } from '@/utils/hooks'

export default function VoteContent({ embedded = false }: { embedded?: boolean }) {
  const navigate = useNavigate()

  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ['vote', 'list'],
    queryFn: ({ pageParam }) => api.voteList(pageParam),
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
      <div className="vote-list">
        {isLoading
          ? [0, 1, 2].map((i) => <Skeleton key={i} style={{ height: 118, marginBottom: 10 }} />)
          : polls.map((poll) => (
              <PollCard key={poll._id} poll={poll} onClick={() => navigate(`/vote/${poll._id}`)} />
            ))}
        {isFetchingNextPage ? <Skeleton style={{ height: 118 }} /> : null}
      </div>

      {!isLoading && !polls.length ? (
        <EmptyView icon="🗳️" title="暂无投票" subtitle="精彩投票马上就来，敬请期待" />
      ) : null}

      <div ref={sentinelRef} />
      {!hasNextPage && polls.length ? <div className="vote-list__footer">— 已经到底啦 —</div> : null}
      {embedded ? null : <TabBar />}
    </div>
  )
}
