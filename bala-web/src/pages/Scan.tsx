import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import type { Html5Qrcode } from 'html5-qrcode'
import { api } from '@/api/endpoints'
import { SectionHeader } from '@/components/common'
import { TopBar } from '@/components/chrome'
import type { Badge, ScanCard } from '@/types/models'
import { rarityLabel } from '@/utils/config'
import { toast } from '@/utils/feedback'

const BADGE_SCAN_THRESHOLD = 3

const FALLBACK_RULES = [
  { type: 'canteen', name: '食堂', desc: '食堂入口海报，扫码参与今日午餐投票' },
  { type: 'library', name: '图书馆', desc: '图书馆一楼公告位，扫码查看读书社团' },
  { type: 'dormitory', name: '宿舍楼', desc: '各楼层电梯口，扫码进入住宿圈' },
  { type: 'bulletin', name: '公告栏', desc: '中央公告栏，扫码查看全校活动' },
  { type: 'classroom', name: '教室区', desc: '教学楼走廊，扫码参与课程相关投票' },
  { type: 'clubroom', name: '社团活动室', desc: '社团活动室门口，扫码直达社团主页' },
  { type: 'sports', name: '体育场馆', desc: '体育馆入口，扫码报名体育赛事' },
  { type: 'gateway', name: '校门', desc: '校门口迎新海报，扫码领取新手勋章' },
]

/** 扫码结果可能是卡号、小程序码 scene 或完整 URL，统一提取 key */
function extractKey(raw: string): string {
  const text = raw.trim()
  if (!text) return ''
  try {
    const url = new URL(text)
    return url.searchParams.get('key') || url.searchParams.get('cardId') || url.searchParams.get('scene') || text
  } catch {
    const match = text.match(/(?:key|cardId|scene)=([A-Za-z0-9-]+)/)
    return match ? match[1] : text
  }
}

export default function Scan() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [key, setKey] = useState('')
  const [card, setCard] = useState<ScanCard | null>(null)
  const [newBadges, setNewBadges] = useState<Badge[]>([])
  const [scanning, setScanning] = useState(false)
  const [checking, setChecking] = useState(false)
  const scannerRef = useRef<Html5Qrcode | null>(null)
  const badgeTimer = useRef<number | null>(null)

  const stopScanner = useCallback(async () => {
    const scanner = scannerRef.current
    scannerRef.current = null
    if (scanner) {
      try {
        await scanner.stop()
        scanner.clear()
      } catch {
        /* 摄像头已停止 */
      }
    }
    setScanning(false)
  }, [])

  useEffect(() => {
    return () => {
      void stopScanner()
      if (badgeTimer.current) window.clearTimeout(badgeTimer.current)
    }
  }, [stopScanner])

  const lookup = useCallback(
    async (raw: string) => {
      const value = extractKey(raw)
      if (!value) return
      try {
        const result = await api.scanCard(value)
        setCard(result)
        setNewBadges([])
        await stopScanner()
      } catch {
        /* toast 已由 api 层弹出 */
      }
    },
    [stopScanner],
  )

  // 支持 /scan?key=xxx、/scan?cardId=xxx、/scan?scene=xxx 深链
  useEffect(() => {
    const deepKey = searchParams.get('key') || searchParams.get('cardId') || searchParams.get('scene')
    if (deepKey) void lookup(deepKey)
  }, [searchParams, lookup])

  async function startScanner() {
    if (scanning) {
      await stopScanner()
      return
    }
    setScanning(true)
    try {
      const { Html5Qrcode } = await import('html5-qrcode')
      const scanner = new Html5Qrcode('scan-reader')
      scannerRef.current = scanner
      await scanner.start(
        { facingMode: 'environment' },
        { fps: 10, qrbox: { width: 220, height: 220 } },
        (decoded) => {
          void lookup(decoded)
        },
        () => undefined,
      )
    } catch {
      setScanning(false)
      scannerRef.current = null
      toast('无法访问摄像头，可改用手动输入卡号（需 HTTPS 或 localhost）')
    }
  }

  async function doCheckin() {
    if (!card || checking) return
    setChecking(true)
    try {
      const result = await api.scanCheckin(card.cardId)
      setCard({
        ...card,
        checked: true,
        tapCount: result.firstTime ? 1 : (card.tapCount || 0) + 1,
        uniqueCards: result.uniqueCards,
      })
      setNewBadges(result.newBadges || [])
      toast('打卡成功')
      void queryClient.invalidateQueries({ queryKey: ['me', 'overview'] })

      if (result.newBadges?.length) {
        if (badgeTimer.current) window.clearTimeout(badgeTimer.current)
        badgeTimer.current = window.setTimeout(() => setNewBadges([]), 3000)
      }

      const target = result.target
      if (target?.type && target.id) {
        window.setTimeout(() => {
          if (target.type === 'vote') navigate(`/vote/${target.id}`)
          else if (target.type === 'club') navigate(`/club/${target.id}`)
          else if (target.type === 'event') navigate(`/calendar?eventId=${target.id}`)
        }, 1200)
      }
    } catch {
      /* toast 已由 api 层弹出 */
    } finally {
      setChecking(false)
    }
  }

  const rules = card?.rules?.length ? card.rules : FALLBACK_RULES
  const locationName =
    rules.find((rule) => rule.type === card?.locationType)?.name || card?.locationType || '未知区域'
  const nextBadgeNeed = Math.max(0, BADGE_SCAN_THRESHOLD - (card?.uniqueCards || 0))

  return (
    <div className="page page--scan page--with-topbar">
      <TopBar back />
      <div className="scan-guide card section fade-up">
        <div className="scan-guide__icon">◎</div>
        <div className="scan-guide__title">叭啦 扫码打卡</div>
        <div className="scan-guide__desc">扫描活动现场的小程序码，解锁不同点位勋章</div>
        <button type="button" className="btn" onClick={startScanner}>
          {scanning ? '关闭摄像头' : '立即扫码'}
        </button>

        {scanning ? (
          <div className="scan-reader">
            <div id="scan-reader" />
            <p className="scan-reader__tip">将二维码对准取景框</p>
          </div>
        ) : null}

        <form
          className="scan-guide__input-row"
          onSubmit={(e) => {
            e.preventDefault()
            void lookup(key)
          }}
        >
          <input
            className="scan-guide__input"
            placeholder="或输入卡片编号，如 QD-CT-01-A01"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            aria-label="卡片编号"
          />
          <button type="submit" className="btn btn--ghost scan-guide__lookup">
            查询
          </button>
        </form>
      </div>

      {card ? (
        <>
          <div className="scan-card card section fade-up">
            <div className="scan-card__title">点位信息</div>
            <div className="scan-card__row">
              <span className="scan-card__label">编号</span>
              <span className="scan-card__value">{card.cardId}</span>
            </div>
            {card.locationDesc ? (
              <div className="scan-card__row">
                <span className="scan-card__label">位置</span>
                <span className="scan-card__value">{card.locationDesc}</span>
              </div>
            ) : null}
            <div className="scan-card__row">
              <span className="scan-card__label">区域</span>
              <span className="scan-card__value">{locationName}</span>
            </div>
            <div className="scan-card__status">
              {card.checked ? (
                <span className="chip chip--success">已打卡</span>
              ) : (
                <span className="chip chip--warning">未打卡</span>
              )}
            </div>
            {!card.checked ? (
              <button type="button" className="btn" disabled={checking} onClick={doCheckin}>
                立即打卡
              </button>
            ) : (
              <div className="scan-card__tip">累计打卡 {card.tapCount || 1} 次</div>
            )}
          </div>

          <div className="scan-progress card section">
            <div className="scan-progress__title">打卡进度</div>
            <div className="scan-progress__ring">
              <div className="scan-progress__num">{card.uniqueCards || 0}</div>
              <div className="scan-progress__label">已打卡点位</div>
            </div>
            <div className="scan-progress__tip">
              {nextBadgeNeed > 0
                ? `再打卡 ${nextBadgeNeed} 个即可解锁「扫码探索者」`
                : '已解锁「扫码探索者」，继续探索更多点位吧'}
            </div>
          </div>
        </>
      ) : null}

      <div className="scan-rules card section">
        <SectionHeader title="点位说明" />
        {rules.map((rule) => (
          <div className="scan-rule" key={rule.type}>
            <span className="scan-rule__dot" />
            <div>
              <div className="scan-rule__name">{rule.name}</div>
              <div className="scan-rule__desc">{rule.desc}</div>
            </div>
          </div>
        ))}
      </div>

      {newBadges.length ? (
        <div className="scan-toast">
          <div className="scan-toast__box pop-in">
            <div className="scan-toast__title">🎉 解锁新勋章</div>
            {newBadges.map((badge) => (
              <div className="scan-toast__badge" key={badge.code}>
                <span className="scan-toast__name">{badge.name}</span>
                <span className="scan-toast__rarity">{rarityLabel[badge.rarity || ''] || badge.rarity}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
