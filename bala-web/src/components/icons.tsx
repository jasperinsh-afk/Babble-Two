/** 线性图标集：首页 / 生活板块复用，避免再依赖字符图标造成语义不清 */
interface IconProps {
  className?: string
}

const stroke = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.9,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
}

/** 扫码：二维码定位块 + 中缝扫描线，一眼可辨 */
export function ScanIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <rect x="3.1" y="3.1" width="6.6" height="6.6" rx="1.7" />
      <rect x="14.3" y="3.1" width="6.6" height="6.6" rx="1.7" />
      <rect x="3.1" y="14.3" width="6.6" height="6.6" rx="1.7" />
      <path d="M14.6 14.6h1.9M18.1 14.6h1.9M14.6 18.1h1.9M18.1 18.1h1.9" />
      <path d="M1.8 12h20.4" />
    </svg>
  )
}

/** 投票：勾选 / 表决 */
export function VoteIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <rect x="3.4" y="4.2" width="17.2" height="15.6" rx="3" />
      <path d="M7.6 12.4l3.1 3.1 5.7-6.6" />
    </svg>
  )
}

/** 生活：屋檐 + 门 */
export function LivingIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <path d="M3.6 11.2 12 4.2l8.4 7" />
      <path d="M5.9 10.4V19.4a1 1 0 0 0 1 1h10.2a1 1 0 0 0 1-1v-9" />
      <path d="M9.9 20.4v-5.2h4.2v5.2" />
    </svg>
  )
}

/** 校园活动日历 */
export function CalendarIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <rect x="3.4" y="5" width="17.2" height="15.6" rx="3" />
      <path d="M3.4 9.8h17.2M8.2 3.2v3.4M15.8 3.2v3.4" />
      <path d="M8.2 14h2.2M13.6 14h2.2M8.2 17.4h2.2M13.6 17.4h2.2" />
    </svg>
  )
}

/** 社团：一群人 */
export function ClubIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <circle cx="9" cy="8.4" r="3.2" />
      <path d="M3.4 20c.5-3.1 2.8-4.8 5.6-4.8s5.1 1.7 5.6 4.8" />
      <path d="M15.6 6.2a3.2 3.2 0 0 1 0 6.4M17.2 15.6c2 .7 3.2 2.3 3.4 4.4" />
    </svg>
  )
}

/** 生活圈：楼栋圈层 / 同好扩散 */
export function CircleIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <circle cx="12" cy="12" r="3" />
      <path d="M18.6 8.4a7.4 7.4 0 0 1 0 7.2M5.4 15.6a7.4 7.4 0 0 1 0-7.2" />
      <path d="M8.6 4.6a9.6 9.6 0 0 1 6.8 0M15.4 19.4a9.6 9.6 0 0 1-6.8 0" />
    </svg>
  )
}

/** 失物招领：搜索 */
export function LostIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <circle cx="10.8" cy="10.8" r="6.6" />
      <path d="M15.8 15.8 20.6 20.6" />
      <path d="M8.6 10.8h4.4M10.8 8.6v4.4" />
    </svg>
  )
}

/** 二手交换：标签 / 交易 */
export function MarketIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <path d="M13.4 3.6H19a1.4 1.4 0 0 1 1.4 1.4v5.6L13.4 3.6z" />
      <path d="M13.4 3.6 20.4 10.6h-4.2a2.8 2.8 0 0 1-2.8-2.8V3.6z" />
      <path d="M10.2 20.4 3.6 13.8l6.6-6.6 6.6 6.6-6.6 6.6z" />
      <path d="M14.4 6.6a1.3 1.3 0 1 1 0 2.6 1.3 1.3 0 0 1 0-2.6z" />
    </svg>
  )
}

export function ChevronLeft({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <path d="M14.6 6.4 8.8 12l5.8 5.6" />
    </svg>
  )
}

export function ChevronRight({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <path d="M9.4 6.4 15.2 12l-5.8 5.6" />
    </svg>
  )
}

/** 未开通 / 施工 */
export function LockIcon({ className }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" {...stroke}>
      <rect x="4.6" y="10.4" width="14.8" height="9.6" rx="2.4" />
      <path d="M8.2 10.4V8a3.8 3.8 0 0 1 7.6 0v2.4" />
      <path d="M12 14.2v2.4" />
    </svg>
  )
}
