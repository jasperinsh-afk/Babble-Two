import assert from 'node:assert/strict'
import { mkdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { chromium } from 'playwright-core'

const BASE = process.env.SMOKE_BASE || 'http://127.0.0.1:5173'
const OUT = path.resolve('logs/ui')
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
  acceptDownloads: true,
  timezoneId: 'Asia/Shanghai',
})
await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: BASE })
const errors = []
context.on('page', (page) => {
  page.on('pageerror', (error) => errors.push(error.message))
})

async function checkCountdown(isoTime, title, units) {
  const page = await context.newPage()
  await page.clock.install({ time: new Date(isoTime) })
  await page.clock.pauseAt(new Date(isoTime))
  await page.goto(`${BASE}/days`, { waitUntil: 'networkidle' })
  assert.equal((await page.locator('.school-countdown__label').innerText()).trim(), title)
  assert.deepEqual(await page.locator('.school-countdown__unit strong').allTextContents(), units)
  await page.close()
  console.log(`countdown ${isoTime}: ${title} ${units.join(':')}`)
}

async function checkAutomaticRollover() {
  const page = await context.newPage()
  const beforeDismissal = new Date('2026-11-06T15:19:59+08:00')
  await page.clock.install({ time: beforeDismissal })
  await page.clock.pauseAt(beforeDismissal)
  await page.goto(`${BASE}/days`, { waitUntil: 'networkidle' })
  assert.equal((await page.locator('.school-countdown__label').innerText()).trim(), '距离放学')
  await page.clock.runFor(2000)
  assert.equal((await page.locator('.school-countdown__label').innerText()).trim(), '距离周一上学')
  await page.close()
  console.log('countdown rollover: 15:19:59 → 15:20:01 passed')
}

try {
  await checkCountdown('2026-11-06T07:00:00+08:00', '距离上学', ['01', '05', '00'])
  await checkCountdown('2026-11-06T16:00:00+08:00', '距离周一上学', ['2', '16', '05', '00'])
  await checkCountdown('2026-11-07T12:00:00+08:00', '距离周一上学', ['1', '20', '05', '00'])
  await checkAutomaticRollover()

  const page = await context.newPage()
  // 桌面无原生分享面板时，验证复制链接的完整兜底流程。
  await page.addInitScript(() => Object.defineProperty(navigator, 'share', { value: undefined, configurable: true }))
  await page.clock.install({ time: new Date('2026-11-06T10:00:00+08:00') })
  await page.clock.pauseAt(new Date('2026-11-06T10:00:00+08:00'))
  await page.goto(`${BASE}/days`, { waitUntil: 'networkidle' })
  assert.equal((await page.locator('.school-countdown__label').innerText()).trim(), '距离放学')
  assert.deepEqual(await page.locator('.school-countdown__unit strong').allTextContents(), ['05', '20', '00'])
  assert.equal(await page.getByRole('link', { name: '生活', exact: true }).count(), 0)
  assert.equal(await page.getByRole('link', { name: '日子', exact: true }).getAttribute('aria-current'), 'page')
  assert.equal(await page.locator('.days-calendar').count(), 1)

  await page.getByRole('button', { name: '列表', exact: true }).click()
  assert.equal(await page.locator('.days-calendar').count(), 0)
  await page.locator('.days-add').click()
  await page.getByRole('button', { name: '保存日子', exact: true }).click()
  assert.match(await page.locator('.day-form__error').innerText(), /起一个名字/)
  await page.getByLabel('日程名称').fill('期末考试')
  await page.getByLabel('日期', { exact: true }).fill('2026-12-01')
  await page.getByLabel(/备注/).fill('认真复习，保持好状态')
  await page.getByRole('button', { name: '保存日子', exact: true }).click()
  await page.locator('.day-schedule').waitFor()
  assert.equal(await page.locator('.day-form').count(), 0)
  assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('bala.days.schedules.v1') || '[]').length), 1)
  assert.equal(await page.getByRole('button', { name: '列表', exact: true }).getAttribute('aria-pressed'), 'true')

  await page.reload({ waitUntil: 'networkidle' })
  await page.getByRole('button', { name: '列表', exact: true }).click()
  assert.equal(await page.locator('.day-schedule').count(), 1)
  await page.screenshot({ path: path.join(OUT, 'days-main.png'), fullPage: true })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)

  await page.locator('.day-schedule').click()
  await page.locator('.day-share-card').waitFor()
  assert.equal(await page.locator('.day-share-card h1').innerText(), '期末考试')
  assert.equal(await page.locator('.day-share-card__count strong').innerText(), '25')
  await page.screenshot({ path: path.join(OUT, 'day-share-page.png'), fullPage: true })

  const downloadEvent = page.waitForEvent('download')
  await page.getByRole('button', { name: '保存图片', exact: true }).click()
  const download = await downloadEvent
  assert.match(download.suggestedFilename(), /\.png$/)
  const imagePath = path.join(OUT, 'day-share-image.png')
  await download.saveAs(imagePath)
  assert.equal(readFileSync(imagePath).subarray(1, 4).toString(), 'PNG')
  console.log(`image download: ${download.suggestedFilename()}`)

  await page.getByRole('button', { name: '分享日子', exact: true }).click()
  await page.waitForFunction(() => document.body.innerText.includes('分享链接已复制'))
  const sharedUrl = await page.evaluate(() => navigator.clipboard.readText())
  assert.match(sharedUrl, /\/days\/share\?/)
  const sharedPage = await context.newPage()
  await sharedPage.goto(sharedUrl, { waitUntil: 'networkidle' })
  assert.equal(await sharedPage.locator('.day-share-card h1').innerText(), '期末考试')
  assert.equal(await sharedPage.locator('.day-detail__delete').count(), 0)
  await sharedPage.close()
  console.log('share link: opened independently')

  page.once('dialog', (dialog) => dialog.accept())
  await page.locator('.day-detail__delete').click()
  await page.waitForURL(`${BASE}/days`)
  assert.equal(await page.evaluate(() => JSON.parse(localStorage.getItem('bala.days.schedules.v1') || '[]').length), 0)

  assert.deepEqual(errors, [])
  console.log('days smoke: all checks passed')
} finally {
  await browser.close()
}
