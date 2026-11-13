const { dayDifference, formatDayDate } = require('./days')

function buildShareQuery(schedule) {
  return [
    'shared=1',
    `title=${encodeURIComponent(schedule.title)}`,
    `date=${encodeURIComponent(schedule.date)}`,
    `note=${encodeURIComponent(schedule.note || '')}`,
  ].join('&')
}

function buildCountdownQuery(item) {
  return [
    'shared=1',
    `title=${encodeURIComponent(item.title)}`,
    `date=${encodeURIComponent(item.date)}`,
    `note=${encodeURIComponent(item.note || '')}`,
    `targetAt=${encodeURIComponent(item.targetAt || '')}`,
    `emoji=${encodeURIComponent(item.emoji || '⏰')}`,
    `badge=${encodeURIComponent(item.badge || '')}`,
  ].join('&')
}

let brandLogoPath = null
function loadBrandLogo() {
  if (brandLogoPath !== null) return Promise.resolve(brandLogoPath)
  return new Promise(resolve => {
    if (typeof wx === 'undefined' || typeof wx.getImageInfo !== 'function') {
      brandLogoPath = ''
      resolve(brandLogoPath)
      return
    }
    wx.getImageInfo({
      src: '/assets/brand/logo-mark.png',
      success: result => { brandLogoPath = result.path; resolve(brandLogoPath) },
      fail: () => { brandLogoPath = ''; resolve(brandLogoPath) },
    })
  })
}

function roundedRect(context, x, y, width, height, radius) {
  context.beginPath()
  context.moveTo(x + radius, y)
  context.lineTo(x + width - radius, y)
  context.quadraticCurveTo(x + width, y, x + width, y + radius)
  context.lineTo(x + width, y + height - radius)
  context.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
  context.lineTo(x + radius, y + height)
  context.quadraticCurveTo(x, y + height, x, y + height - radius)
  context.lineTo(x, y + radius)
  context.quadraticCurveTo(x, y, x + radius, y)
  context.closePath()
}

function setFont(context, size, weight = 400) {
  context.font = `${weight} ${size}px "PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei", sans-serif`
}

function drawBrandHeader(context, logoPath = '') {
  context.setTextAlign('left')
  context.setTextBaseline('top')
  let drawn = false
  if (logoPath) {
    try {
      context.drawImage(logoPath, 60, 62, 42, 36)
      drawn = true
    } catch (error) {
      drawn = false
    }
  }
  if (!drawn) {
    roundedRect(context, 60, 62, 42, 36, 10)
    const mark = context.createLinearGradient(60, 62, 102, 98)
    mark.addColorStop(0, '#8B5CF6')
    mark.addColorStop(1, '#F97316')
    context.setFillStyle(mark)
    context.fill()
    setFont(context, 16, 600)
    context.setFillStyle('#FFFFFF')
    context.fillText('叭', 72, 69)
  }
  setFont(context, 22, 500)
  context.setFillStyle('#1E1B2E')
  context.fillText('叭啦·过日子', 116, 68)
}

function wrapText(context, text, maxWidth, maxLines) {
  const characters = Array.from(text)
  const lines = []
  let line = ''
  let consumed = 0
  for (const character of characters) {
    const candidate = line + character
    if (line && context.measureText(candidate).width > maxWidth) {
      lines.push(line)
      consumed += Array.from(line).length
      line = character
      if (lines.length === maxLines) break
    } else {
      line = candidate
    }
  }
  if (lines.length < maxLines && line) {
    lines.push(line)
    consumed += Array.from(line).length
  }
  if (consumed < characters.length && lines.length) {
    let last = lines[lines.length - 1]
    while (last && context.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1)
    lines[lines.length - 1] = `${last}…`
  }
  return lines
}

function drawSchedule(context, schedule, now = new Date(), logoPath = '') {
  const background = context.createLinearGradient(0, 0, 540, 675)
  background.addColorStop(0, '#EEE6FF')
  background.addColorStop(0.52, '#FAF8FF')
  background.addColorStop(1, '#FFF0E5')
  context.setFillStyle(background)
  context.fillRect(0, 0, 540, 675)

  context.setShadow(0, 10, 25, 'rgba(64,43,105,0.12)')
  roundedRect(context, 32, 35, 476, 605, 26)
  context.setFillStyle('#FFFFFF')
  context.fill()
  context.setShadow(0, 0, 0, 'rgba(0,0,0,0)')

  drawBrandHeader(context, logoPath)
  setFont(context, 15)
  context.setFillStyle('#9D96B8')
  context.fillText(formatDayDate(schedule.date), 60, 141)

  setFont(context, 31, 600)
  context.setFillStyle('#1E1B2E')
  const titleLines = wrapText(context, schedule.title, 415, 2)
  titleLines.forEach((line, index) => context.fillText(line, 60, 181 + index * 42))

  const difference = dayDifference(schedule.date, now)
  const count = Math.abs(difference)
  setFont(context, 17, 500)
  context.setFillStyle('#8B5CF6')
  context.fillText(difference === 0 ? '就是今天' : difference > 0 ? '还有' : '已经', 60, 305)

  const numberSize = count >= 10000 ? 75 : count >= 1000 ? 90 : 110
  setFont(context, numberSize, 700)
  const numberGradient = context.createLinearGradient(60, 325, 310, 450)
  numberGradient.addColorStop(0, '#7C3AED')
  numberGradient.addColorStop(1, '#F97316')
  context.setFillStyle(numberGradient)
  context.fillText(String(count), 56, 325)
  const numberWidth = context.measureText(String(count)).width
  setFont(context, 23, 500)
  context.setFillStyle('#5C5775')
  context.fillText('天', Math.min(60 + numberWidth + 14, 440), 395)

  if (schedule.note) {
    setFont(context, 16)
    context.setFillStyle('#5C5775')
    const noteLines = wrapText(context, schedule.note, 410, 3)
    noteLines.forEach((line, index) => context.fillText(line, 60, 500 + index * 25))
  }

}

function countdownUnits(targetAt, now = new Date()) {
  const target = new Date(targetAt)
  const total = Number.isFinite(target.getTime())
    ? Math.max(0, Math.ceil((target.getTime() - now.getTime()) / 1000))
    : 0
  const pad = value => String(value).padStart(2, '0')
  return {
    days: Math.floor(total / 86400),
    hours: pad(Math.floor((total % 86400) / 3600)),
    minutes: pad(Math.floor((total % 3600) / 60)),
    seconds: pad(total % 60),
  }
}

function drawCountdown(context, item, now = new Date(), logoPath = '') {
  const background = context.createLinearGradient(0, 0, 540, 675)
  background.addColorStop(0, '#EEE6FF')
  background.addColorStop(0.52, '#FAF8FF')
  background.addColorStop(1, '#FFF0E5')
  context.setFillStyle(background)
  context.fillRect(0, 0, 540, 675)

  context.setShadow(0, 10, 25, 'rgba(64,43,105,0.12)')
  roundedRect(context, 32, 35, 476, 605, 26)
  context.setFillStyle('#FFFFFF')
  context.fill()
  context.setShadow(0, 0, 0, 'rgba(0,0,0,0)')

  drawBrandHeader(context, logoPath)
  setFont(context, 15)
  context.setFillStyle('#9D96B8')
  context.fillText(formatDayDate(item.date), 60, 141)

  setFont(context, 31, 600)
  context.setFillStyle('#1E1B2E')
  const titleLines = wrapText(context, item.title, 415, 2)
  titleLines.forEach((line, index) => context.fillText(line, 60, 181 + index * 42))

  const units = countdownUnits(item.targetAt, now)
  setFont(context, 17, 500)
  context.setFillStyle('#8B5CF6')
  context.fillText(units.days > 0 ? '还有' : '就在今天', 60, 305)

  const numberSize = units.days >= 1000 ? 78 : 110
  setFont(context, numberSize, 700)
  const numberGradient = context.createLinearGradient(60, 325, 310, 450)
  numberGradient.addColorStop(0, '#7C3AED')
  numberGradient.addColorStop(1, '#F97316')
  context.setFillStyle(numberGradient)
  context.fillText(String(units.days), 56, 325)
  const numberWidth = context.measureText(String(units.days)).width
  setFont(context, 23, 500)
  context.setFillStyle('#5C5775')
  context.fillText('天', Math.min(60 + numberWidth + 14, 440), 395)

  setFont(context, 24, 600)
  context.setFillStyle('#5C5775')
  context.fillText(`${units.hours} : ${units.minutes} : ${units.seconds}`, 60, 455)

  if (item.note) {
    setFont(context, 16)
    context.setFillStyle('#5C5775')
    const noteLines = wrapText(context, item.note, 410, 3)
    noteLines.forEach((line, index) => context.fillText(line, 60, 505 + index * 25))
  }

}

async function createCountdownImage(page, item, now = new Date()) {
  const logoPath = await loadBrandLogo()
  return new Promise((resolve, reject) => {
    try {
      const context = wx.createCanvasContext('dayShareCanvas', page)
      drawCountdown(context, item, now, logoPath)
      context.draw(false, () => {
        wx.canvasToTempFilePath({
          canvasId: 'dayShareCanvas',
          x: 0,
          y: 0,
          width: 540,
          height: 675,
          destWidth: 1080,
          destHeight: 1350,
          fileType: 'png',
          quality: 1,
          success: result => resolve(result.tempFilePath),
          fail: reject,
        }, page)
      })
    } catch (error) {
      reject(error)
    }
  })
}

async function createScheduleImage(page, schedule, now = new Date()) {
  const logoPath = await loadBrandLogo()
  return new Promise((resolve, reject) => {
    try {
      const context = wx.createCanvasContext('dayShareCanvas', page)
      drawSchedule(context, schedule, now, logoPath)
      context.draw(false, () => {
        wx.canvasToTempFilePath({
          canvasId: 'dayShareCanvas',
          x: 0,
          y: 0,
          width: 540,
          height: 675,
          destWidth: 1080,
          destHeight: 1350,
          fileType: 'png',
          quality: 1,
          success: result => resolve(result.tempFilePath),
          fail: reject,
        }, page)
      })
    } catch (error) {
      reject(error)
    }
  })
}

module.exports = {
  buildShareQuery,
  buildCountdownQuery,
  wrapText,
  drawSchedule,
  drawCountdown,
  drawBrandHeader,
  loadBrandLogo,
  countdownUnits,
  createScheduleImage,
  createCountdownImage,
}
