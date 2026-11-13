/**
 * 校园服务目录：投票以外的全部功能都收敛到「生活」板块，
 * 由这里统一定义名称、说明、图标与真实路由，避免各处硬编码。
 */
import { useNavigate } from 'react-router-dom'
import type { ComponentType } from 'react'
import {
  CalendarIcon,
  CircleIcon,
  ClubIcon,
  LostIcon,
  MarketIcon,
  ScanIcon,
} from '@/components/icons'
import { SERVICE_OPENED } from '@/utils/config'
import { showServiceNotice } from '@/utils/notice'

export interface CampusService {
  key: string
  label: string
  desc: string
  /** 开通后跳转的真实路由 */
  route: string
  Icon: ComponentType<{ className?: string }>
}

export const CAMPUS_SERVICES: CampusService[] = [
  {
    key: 'calendar',
    label: '校园活动',
    desc: '讲座、赛事与社团活动，按日历查看',
    route: '/calendar',
    Icon: CalendarIcon,
  },
  {
    key: 'club',
    label: '社团广场',
    desc: '加入兴趣社团，追更社团动态',
    route: '/club',
    Icon: ClubIcon,
  },
  {
    key: 'circle',
    label: '生活圈',
    desc: '楼栋里的新鲜事与互助信息',
    route: '/living?view=circle',
    Icon: CircleIcon,
  },
  {
    key: 'lost',
    label: '失物招领',
    desc: '丢东西或捡到东西，登记一下',
    route: '/living?view=lost',
    Icon: LostIcon,
  },
  {
    key: 'market',
    label: '二手交换',
    desc: '校内闲置流转，当面交易更放心',
    route: '/living?view=market',
    Icon: MarketIcon,
  },
  {
    key: 'scan',
    label: '扫码打卡',
    desc: '扫描点位码，收集校园勋章',
    route: '/scan',
    Icon: ScanIcon,
  },
]

export function findService(key: string): CampusService | undefined {
  return CAMPUS_SERVICES.find((service) => service.key === key)
}

/**
 * 统一入口：未开通时弹「校区尚未开通该服务」，开通后跳转到真实页面。
 * 返回 false 表示这不是已登记的服务（调用方按普通路由处理）。
 */
export function useOpenService() {
  const navigate = useNavigate()
  return (key: string): boolean => {
    const service = findService(key)
    if (!service) return false
    if (!SERVICE_OPENED) {
      showServiceNotice(key)
      return true
    }
    navigate(service.route)
    return true
  }
}
