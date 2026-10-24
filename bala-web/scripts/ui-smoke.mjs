/**
 * 网页版 UI 冒烟脚本（开发辅助，使用本机 Chrome，无需下载浏览器）
 * 用法：先启动 vite(5173) 与 uvicorn(8000)，再执行 node scripts/ui-smoke.mjs
 */
import { chromium } from 'playwright-core'
import { mkdirSync } from 'node:fs'
import path from 'node:path'

const BASE = process.env.SMOKE_BASE || 'http://127.0.0.1:5173'
const OUT = path.resolve('logs/ui')
mkdirSync(OUT, { recursive: true })

const PAGES = [
  ['home', '/home'],
  ['campus', '/campus'],
  ['messages', '/messages'],
  ['vote-list', '/vote'],
  ['vote-detail', '/vote/p001'],
  ['club-list', '/club'],
  ['club-detail', '/club/c001'],
  ['calendar', '/calendar'],
  ['living', '/living'],
  ['scan', '/scan'],
  ['profile', '/profile'],
]

const browser = await chromium.launch({ channel: 'chrome', headless: true })
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 2,
  isMobile: true,
  hasTouch: true,
})
const page = await context.newPage()

const errors = []
page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`))
page.on('console', (msg) => {
  if (msg.type() === 'error') errors.push(`console: ${msg.text()} @ ${msg.location()?.url || ''}`)
})
page.on('response', (res) => {
  if (res.status() >= 400) errors.push(`http ${res.status()}: ${res.url()}`)
})

for (const [name, route] of PAGES) {
  await page.goto(`${BASE}${route}`, { waitUntil: 'load', timeout: 45000 })
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
  await page.waitForTimeout(800)
  const metrics = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    text: document.body.innerText.length,
  }))
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true })
  console.log(
    `${name.padEnd(13)} width=${metrics.scrollWidth}/${metrics.innerWidth} text=${metrics.text}`,
  )
}

// 首页布局细节
await page.goto(`${BASE}/home`, { waitUntil: 'load' })
const home = await page.evaluate(() => {
  const rect = (sel) => {
    const el = document.querySelector(sel)
    if (!el) return null
    const r = el.getBoundingClientRect()
    return { x: Math.round(r.x), right: Math.round(r.right), width: Math.round(r.width) }
  }
  return {
    quickItems: document.querySelectorAll('.home-quick__item').length,
    scanButton: rect('.home-header__scan'),
    lastQuick: rect('.home-quick__item:last-child'),
    shell: rect('.app-shell'),
  }
})
console.log('home layout:', JSON.stringify(home))

// 投票交互：选项 → 提交 → 结果
await page.goto(`${BASE}/vote/p001`, { waitUntil: 'load' })
await page.locator('.vote-option').first().click()
await page.locator('.action-dock .btn').click()
await page.waitForTimeout(1500)
const resultVisible = await page.locator('.result-chart').count()
console.log(`vote flow: result chart = ${resultVisible ? 'visible' : 'MISSING'}`)
await page.screenshot({ path: path.join(OUT, 'vote-after-cast.png'), fullPage: true })

console.log(errors.length ? `ERRORS:\n${errors.join('\n')}` : 'no console/page errors')
await browser.close()
