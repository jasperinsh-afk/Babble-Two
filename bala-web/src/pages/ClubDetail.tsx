import { useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/endpoints'
import { EmptyView, SectionHeader, Skeleton, SmartImage } from '@/components/common'
import { TopBar } from '@/components/chrome'
import { clubCategoryLabel } from '@/utils/config'
import { toast } from '@/utils/feedback'

export default function ClubDetail() {
  const { clubId = '' } = useParams()
  const queryClient = useQueryClient()

  const { data: club, isLoading } = useQuery({
    queryKey: ['club', 'detail', clubId],
    queryFn: () => api.clubDetail(clubId),
    enabled: Boolean(clubId),
  })

  const { data: postsData, isLoading: postsLoading } = useQuery({
    queryKey: ['club', 'posts', clubId],
    queryFn: () => api.clubPosts(clubId),
    enabled: Boolean(clubId),
  })

  const joinMutation = useMutation<unknown, Error, boolean>({
    mutationFn: (joined: boolean) => (joined ? api.clubLeave(clubId) : api.clubJoin(clubId)),
    onSuccess: async (_, wasJoined) => {
      toast(wasJoined ? '已退出社团' : '加入成功')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['club', 'detail', clubId] }),
        queryClient.invalidateQueries({ queryKey: ['club', 'list'] }),
        queryClient.invalidateQueries({ queryKey: ['me', 'overview'] }),
      ])
    },
  })

  const posts = postsData?.list ?? []

  return (
    <div className="page page--club-detail page--with-topbar">
      <TopBar back />
      {isLoading || !club ? (
        <div className="section">
          <Skeleton style={{ height: 160, marginBottom: 16 }} />
          <Skeleton style={{ height: 200 }} />
          {!isLoading && !club ? <EmptyView icon="🏛️" title="社团不存在" /> : null}
        </div>
      ) : (
        <>
          <div className="club-hero fade-up">
            <SmartImage
              className="club-hero__cover"
              src={club.coverUrl}
              alt={club.name}
              fallback={<span>{(club.name || '社').charAt(0)}</span>}
            />
            <div className="club-hero__body">
              <div className="club-hero__name-row">
                <h1 className="club-hero__name">{club.name}</h1>
                {club.isVerified ? <span className="club-hero__verified">官方认证</span> : null}
              </div>
              <p className="club-hero__desc">{club.description || ''}</p>
              <div className="club-hero__meta">
                <span className="chip">{clubCategoryLabel[club.category || ''] || club.category}</span>
                <span className="club-hero__count">
                  {club.memberCount || 0} 成员 · 热度 {club.heatScore || 0}
                </span>
              </div>
              <button
                type="button"
                className={`club-hero__btn btn ${club.joined ? 'btn--ghost' : ''}`}
                disabled={joinMutation.isPending}
                onClick={() => joinMutation.mutate(Boolean(club.joined))}
              >
                {club.joined ? '已加入' : '加入社团'}
              </button>
            </div>
          </div>

          <section className="section">
            <SectionHeader title="社团动态" />
            <div className="club-posts">
              {posts.map((post) => (
                <article className="club-post" key={post._id}>
                  {post.title ? <h3 className="club-post__title">{post.title}</h3> : null}
                  <p className="club-post__content">{post.content}</p>
                  {post.images?.length ? (
                    <div className="club-post__images">
                      {post.images.map((img) => (
                        <SmartImage className="club-post__img" key={img} src={img} alt={post.title} />
                      ))}
                    </div>
                  ) : null}
                  <div className="club-post__footer">
                    {post.isPinned ? <span className="club-post__pinned">置顶</span> : <span />}
                    <span className="club-post__likes">{post.likeCount || 0} 赞</span>
                  </div>
                </article>
              ))}
              {postsLoading ? <Skeleton style={{ height: 120 }} /> : null}
              {!postsLoading && !posts.length ? (
                <EmptyView icon="📰" title="暂无动态" subtitle="精彩内容即将发布" />
              ) : null}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
