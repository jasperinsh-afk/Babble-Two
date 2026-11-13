/**
 * 「生活」板块：投票以外的全部校园功能都在这里入口
 * （社团 / 活动日历 / 生活圈 / 失物招领 / 二手交换 / 扫码打卡）
 * 当前校区尚未开通，点击任一服务统一提示「校区尚未开通该服务」；
 * 开关 SERVICE_OPENED 置为 true 后，各入口会落到真实页面。
 */
import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import LivingContent from '@/components/content/LivingContent'
import { SectionHeader } from '@/components/common'
import { TabBar, TopBar } from '@/components/chrome'
import { ChevronRight, VoteIcon } from '@/components/icons'
import { CAMPUS_SERVICES, useOpenService } from '@/components/services'
import { SERVICE_OPENED } from '@/utils/config'
import { showServiceNotice } from '@/utils/notice'

/** 生活类子服务 → LivingContent 内部 Tab */
const SUB_VIEWS: Record<string, { title: string; tab: number }> = {
  circle: { title: '生活圈', tab: 0 },
  lost: { title: '失物招领', tab: 1 },
  market: { title: '二手交换', tab: 2 },
}

export default function Living() {
  const [searchParams, setSearchParams] = useSearchParams()
  const openService = useOpenService()
  const navigate = useNavigate()
  const view = searchParams.get('view') || ''

  // 未开通的服务即使手动拼 URL 也回到卡片墙并提示未开通
  useEffect(() => {
    if (!view || SERVICE_OPENED) return
    setSearchParams({}, { replace: true })
    showServiceNotice(view)
  }, [view, setSearchParams])

  const subView = SERVICE_OPENED ? SUB_VIEWS[view] : undefined

  return (
    <div className="page page--living page--with-topbar">
      <TopBar title={subView ? subView.title : '生活'} back={Boolean(subView)} />

      {subView ? (
        <LivingContent embedded initialTab={subView.tab} />
      ) : (
        <>
          <section className="section living-hero">
            <span className="living-hero__pill">逐步开放中</span>
            <div className="living-hero__title">校区尚未开通该服务</div>
            <div className="living-hero__text">
              投票功能已全量开放；下面的校园生活服务正在逐校开通，开通后会在这里第一时间通知你。
            </div>
          </section>

          <section className="section">
            <SectionHeader title="校园生活服务" />
            <div className="living-grid">
              {CAMPUS_SERVICES.map((service) => {
                const Glyph = service.Icon
                return (
                  <button
                    type="button"
                    key={service.key}
                    className={`service-card ${SERVICE_OPENED ? '' : 'service-card--locked'}`}
                    onClick={() => openService(service.key)}
                  >
                    <span className={`service-card__icon service-card__icon--${service.key}`}>
                      <Glyph className="service-card__glyph" />
                    </span>
                    <span className="service-card__body">
                      <span className="service-card__name">{service.label}</span>
                      <span className="service-card__desc">{service.desc}</span>
                    </span>
                    <span className="service-card__status">
                      {SERVICE_OPENED ? '已开通' : '未开通'}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>

          <section className="section">
            <button type="button" className="living-vote" onClick={() => navigate('/vote')}>
              <VoteIcon className="living-vote__icon" />
              <span className="living-vote__body">
                <span className="living-vote__title">投票广场</span>
                <span className="living-vote__text">全校热门投票正在进行，去投一票</span>
              </span>
              <ChevronRight className="living-vote__arrow" />
            </button>
          </section>
        </>
      )}

      <TabBar />
    </div>
  )
}
