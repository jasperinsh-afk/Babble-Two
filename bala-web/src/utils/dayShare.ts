import { dayDifference, formatDayDate, type DaySchedule } from '@/utils/days'

function roundedRect(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  context.beginPath()
  context.moveTo(x + radius, y)
  context.arcTo(x + width, y, x + width, y + height, radius)
  context.arcTo(x + width, y + height, x, y + height, radius)
  context.arcTo(x, y + height, x, y, radius)
  context.arcTo(x, y, x + width, y, radius)
  context.closePath()
}

function wrapText(
  context: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  maxLines: number,
): string[] {
  const lines: string[] = []
  let line = ''
  for (const character of Array.from(text)) {
    const candidate = line + character
    if (line && context.measureText(candidate).width > maxWidth) {
      lines.push(line)
      line = character
      if (lines.length === maxLines) break
    } else {
      line = candidate
    }
  }
  if (lines.length < maxLines && line) lines.push(line)
  const consumed = lines.join('').length
  if (consumed < Array.from(text).length && lines.length) {
    let last = lines[lines.length - 1]
    while (last && context.measureText(`${last}…`).width > maxWidth) {
      last = last.slice(0, -1)
    }
    lines[lines.length - 1] = `${last}…`
  }
  return lines
}

export function scheduleImageName(schedule: DaySchedule): string {
  const safeTitle = schedule.title.replace(/[\\/:*?"<>|]/g, '-').slice(0, 30) || '我的日子'
  return `${safeTitle}-${schedule.date}.png`
}

let brandLogo: Promise<HTMLImageElement | null> | null = null

function loadBrandLogo(): Promise<HTMLImageElement | null> {
  if (!brandLogo) {
    brandLogo = new Promise((resolve) => {
      const image = new Image()
      image.onload = () => resolve(image)
      image.onerror = () => resolve(null)
      image.src = '/assets/brand/logo-mark.png'
    })
  }
  return brandLogo
}

export async function createScheduleImage(schedule: DaySchedule, now = new Date()): Promise<Blob> {
  const canvas = document.createElement('canvas')
  canvas.width = 1080
  canvas.height = 1350
  const context = canvas.getContext('2d')
  if (!context) return Promise.reject(new Error('当前浏览器不支持图片生成'))
  const logo = await loadBrandLogo()

  const background = context.createLinearGradient(0, 0, 1080, 1350)
  background.addColorStop(0, '#eee6ff')
  background.addColorStop(0.52, '#faf8ff')
  background.addColorStop(1, '#fff0e5')
  context.fillStyle = background
  context.fillRect(0, 0, 1080, 1350)

  context.shadowColor = 'rgba(64, 43, 105, 0.12)'
  context.shadowBlur = 50
  context.shadowOffsetY = 20
  roundedRect(context, 64, 70, 952, 1210, 52)
  context.fillStyle = '#ffffff'
  context.fill()
  context.shadowColor = 'transparent'

  context.textBaseline = 'top'
  if (logo) {
    context.drawImage(logo, 120, 124, 84, 72)
  } else {
    context.fillStyle = '#8b5cf6'
    roundedRect(context, 120, 124, 84, 72, 20)
    context.fill()
  }
  context.fillStyle = '#1e1b2e'
  context.font = '500 44px "PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif'
  context.fillText('叭啦·过日子', 232, 136)

  context.fillStyle = '#9d96b8'
  context.font = '400 31px "PingFang SC", "Microsoft YaHei", sans-serif'
  context.fillText(formatDayDate(schedule.date), 120, 282)

  context.fillStyle = '#1e1b2e'
  context.font = '600 62px "PingFang SC", "Microsoft YaHei", sans-serif'
  const titleLines = wrapText(context, schedule.title, 830, 2)
  titleLines.forEach((line, index) => context.fillText(line, 120, 362 + index * 84))

  const difference = dayDifference(schedule.date, now)
  const countLabel = difference === 0 ? '就是今天' : difference > 0 ? '还有' : '已经'
  const count = Math.abs(difference)
  context.fillStyle = '#8b5cf6'
  context.font = '500 34px "PingFang SC", "Microsoft YaHei", sans-serif'
  context.fillText(countLabel, 120, 610)

  const numberSize = count >= 10000 ? 150 : count >= 1000 ? 180 : 220
  context.font = `700 ${numberSize}px -apple-system, "Segoe UI", sans-serif`
  const numberGradient = context.createLinearGradient(120, 650, 620, 900)
  numberGradient.addColorStop(0, '#7c3aed')
  numberGradient.addColorStop(1, '#f97316')
  context.fillStyle = numberGradient
  context.fillText(String(count), 112, 650)
  const numberWidth = context.measureText(String(count)).width
  context.fillStyle = '#5c5775'
  context.font = '500 46px "PingFang SC", "Microsoft YaHei", sans-serif'
  context.fillText('天', Math.min(120 + numberWidth + 28, 880), 790)

  if (schedule.note) {
    context.fillStyle = '#5c5775'
    context.font = '400 32px "PingFang SC", "Microsoft YaHei", sans-serif'
    const noteLines = wrapText(context, schedule.note, 820, 3)
    noteLines.forEach((line, index) => context.fillText(line, 120, 1000 + index * 50))
  }

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('图片生成失败，请重试'))
    }, 'image/png')
  })
}

export async function downloadScheduleImage(schedule: DaySchedule): Promise<string> {
  const blob = await createScheduleImage(schedule)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = scheduleImageName(schedule)
  document.body.appendChild(link)
  link.click()
  link.remove()
  return url
}

export function scheduleShareUrl(schedule: DaySchedule): string {
  const params = new URLSearchParams({
    title: schedule.title,
    date: schedule.date,
    note: schedule.note,
  })
  return `${window.location.origin}/days/share?${params.toString()}`
}

export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    // 继续尝试兼容旧浏览器的复制方式。
  }
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  let copied = false
  try {
    copied = document.execCommand('copy')
  } catch {
    copied = false
  }
  textarea.remove()
  return copied
}
