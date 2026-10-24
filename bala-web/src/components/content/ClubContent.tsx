import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { ClubCard } from '@/components/cards'
import { EmptyView, Skeleton } from '@/components/common'
import { TabBar } from '@/components/chrome'
import { useInfiniteScroll } from '@/utils/hooks'

const TABS = [
  { category: 'all', label: '全部' },
  { category: 'academic', label: '学术' },
  { category: 'sports', label: '体育' },
  { category: 'art', label: '艺术' },
  { category: 'charity', label: '公益' },
  { category: 'interest', label: '兴趣' },
]

export default function ClubContent({ embedded = false }: { embedded?: boolean }) {
  const [category, setCategory] = useState('all')
  const [input, setInput] = useState('')
  const [keyword, setKeyword] = useState('')
  const navigate = useNavigate()

  const { data, isLoading, hasNextPage, fetchNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ['club', 'list', category, keyword],
    queryFn: ({ pageParam }) => api.clubList(category, keyword, pageParam),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => (lastPage.hasMore ? pages.length : undefined),
  })

  const clubs = data?.pages.flatMap((page) => page.list) ?? []
  const sentinelRef = useInfiniteScroll(
    () => {
      if (hasNextPage && !isFetchingNextPage) void fetchNextPage()
    },
    Boolean(hasNextPage),
  )

  return (
    <div className={`${embedded ? '' : 'page'} page--club-list`}>
      <form
        className="club-search"
        onSubmit={(e) => {
          e.preventDefault()
          setKeyword(input.trim())
        }}
      >
        <input
          className="club-search__input"
          placeholder="搜索社团名称"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          aria-label="搜索社团名称"
        />
      </form>

      <div className="club-tabs">
        <div className="club-tabs__scroll">
          <div className="club-tabs__wrap">
            {TABS.map((tab) => (
              <button
                type="button"
                key={tab.category}
                className={`club-tabs__item ${category === tab.category ? 'club-tabs__item--active' : ''}`}
                onClick={() => setCategory(tab.category)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="club-grid">
        {clubs.map((club) => (
          <div className="club-grid__cell" key={club._id}>
            <ClubCard club={club} onClick={() => navigate(`/club/${club._id}`)} />
          </div>
        ))}
      </div>

      {isLoading || isFetchingNextPage ? (
        <div className="club-grid">
          {[0, 1].map((i) => (
            <Skeleton key={i} style={{ width: '49%', height: 168 }} />
          ))}
        </div>
      ) : null}

      {!isLoading && !clubs.length ? (
        <EmptyView icon="🏛️" title="暂无社团" subtitle="换个关键词或分类试试看" />
      ) : null}

      <div ref={sentinelRef} />
      {embedded ? null : <TabBar />}
    </div>
  )
}
