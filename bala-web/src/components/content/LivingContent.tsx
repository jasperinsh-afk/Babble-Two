import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { EmptyView, Skeleton, SmartImage } from '@/components/common'
import { TopBar } from '@/components/chrome'
import { fromNowText, priceText } from '@/utils/format'

const TABS = ['生活圈', '失物招领', '二手交换']
const KINDS = [
  { key: 'all', label: '全部' },
  { key: 'lost', label: '寻物' },
  { key: 'found', label: '招领' },
]

export default function LivingContent({ embedded = false }: { embedded?: boolean }) {
  const [tab, setTab] = useState(0)
  const [channelId, setChannelId] = useState('')
  const [kind, setKind] = useState('all')

  const { data: channelData } = useQuery({
    queryKey: ['living', 'channels'],
    queryFn: () => api.livingChannels(),
  })
  const channels = channelData?.list ?? []

  useEffect(() => {
    if (!channelId && channels.length) setChannelId(channels[0]._id)
  }, [channels, channelId])

  const { data: postData, isLoading: postsLoading } = useQuery({
    queryKey: ['living', 'channelPosts', channelId],
    queryFn: () => api.livingChannelPosts(channelId),
    enabled: tab === 0 && Boolean(channelId),
  })

  const { data: lostData, isLoading: lostLoading } = useQuery({
    queryKey: ['living', 'lostFound', kind],
    queryFn: () => api.livingLostFound(kind),
    enabled: tab === 1,
  })

  const { data: secondData, isLoading: secondLoading } = useQuery({
    queryKey: ['living', 'secondHand'],
    queryFn: () => api.livingSecondHand(),
    enabled: tab === 2,
  })

  const posts = postData?.list ?? []
  const lostItems = lostData?.list ?? []
  const secondItems = secondData?.list ?? []

  return (
    <div
      className={`${embedded ? '' : 'page'} page--living ${
        embedded ? '' : 'page--with-topbar'
      }`}
    >
      {embedded ? null : <TopBar back />}
      <div className="living-tabs" role="tablist">
        {TABS.map((label, index) => (
          <button
            type="button"
            role="tab"
            aria-selected={tab === index}
            key={label}
            className={`living-tabs__item ${tab === index ? 'living-tabs__item--active' : ''}`}
            onClick={() => setTab(index)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 0 ? (
        <div>
          <div className="living-channels">
            <div className="living-channels__wrap">
              {channels.map((channel) => (
                <button
                  type="button"
                  key={channel._id}
                  className={`living-channels__item ${
                    channelId === channel._id ? 'living-channels__item--active' : ''
                  }`}
                  onClick={() => setChannelId(channel._id)}
                >
                  {channel.name}
                </button>
              ))}
            </div>
          </div>

          <div className="living-posts">
            {posts.map((post) => (
              <article className="living-post" key={post._id}>
                <p className="living-post__content">{post.content}</p>
                {post.images?.length ? (
                  <div className="living-post__images">
                    {post.images.map((img) => (
                      <SmartImage className="living-post__img" key={img} src={img} alt="宿舍帖子配图" />
                    ))}
                  </div>
                ) : null}
                <div className="living-post__footer">
                  <span className="living-post__likes">{post.likeCount || 0} 赞</span>
                  <span className="living-post__time">{fromNowText(post.createdAt)}</span>
                </div>
              </article>
            ))}
            {postsLoading ? <Skeleton style={{ height: 110 }} /> : null}
            {!postsLoading && !posts.length ? (
              <EmptyView icon="🏠" title="暂无帖子" subtitle="换个频道看看" />
            ) : null}
          </div>
        </div>
      ) : null}

      {tab === 1 ? (
        <div>
          <div className="living-kind">
            {KINDS.map((item) => (
              <button
                type="button"
                key={item.key}
                className={`living-kind__item ${kind === item.key ? 'living-kind__item--active' : ''}`}
                onClick={() => setKind(item.key)}
              >
                {item.label}
              </button>
            ))}
          </div>

          <div className="living-cards">
            {lostItems.map((item) => (
              <article className="living-card" key={item._id}>
                <div className="living-card__top">
                  <span className="living-card__title">{item.title}</span>
                  <span className={`chip chip--${item.kind === 'lost' ? 'warning' : 'success'}`}>
                    {item.kind === 'lost' ? '寻物' : '招领'}
                  </span>
                </div>
                {item.description ? <p className="living-card__desc">{item.description}</p> : null}
                {item.location ? <div className="living-card__meta">📍 {item.location}</div> : null}
                {item.contact ? <div className="living-card__meta">📞 {item.contact}</div> : null}
              </article>
            ))}
            {lostLoading ? <Skeleton style={{ height: 110 }} /> : null}
            {!lostLoading && !lostItems.length ? (
              <EmptyView icon="🔍" title="暂无信息" subtitle="暂无相关失物招领" />
            ) : null}
          </div>
        </div>
      ) : null}

      {tab === 2 ? (
        <div className="living-second">
          {secondItems.map((item) => (
            <article className="living-second__item" key={item._id}>
              <div className="living-second__title">{item.title}</div>
              <div className="living-second__price">{priceText(item.price)}</div>
              {item.description ? <p className="living-second__desc">{item.description}</p> : null}
              {item.contact ? <div className="living-second__contact">联系：{item.contact}</div> : null}
            </article>
          ))}
          {secondLoading ? <Skeleton style={{ height: 110 }} /> : null}
          {!secondLoading && !secondItems.length ? (
            <EmptyView icon="🛍️" title="暂无商品" subtitle="暂时没有二手物品" />
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
