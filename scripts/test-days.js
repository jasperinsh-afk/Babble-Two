process.env.TZ = 'Asia/Shanghai'

const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const root = path.resolve(__dirname, '../miniprogram')
const {
  toDateKey,
  isDateKey,
  dayDifference,
  readSchedules,
  writeSchedules,
  getSchoolCountdown,
} = require(path.join(root, 'utils/days'))
const {
  buildShareQuery,
  buildCountdownQuery,
  drawSchedule,
  drawCountdown,
  drawBrandHeader,
  countdownUnits,
  createScheduleImage,
  createCountdownImage,
} = require(path.join(root, 'utils/dayShare'))
const {
  POINTS,
  MEDAL_NAME,
  weekStart,
  weekKey,
  previousWeekStart,
  sanitizeNickname,
  aggregateRecords,
  rankNumber,
} = require(path.join(__dirname, '../cloudfunctions/leaderboard/score'))

const storage = {}
let canvasOptions = null
let cloudResponses = {}
const cloudFailures = new Set()
const gradient = { addColorStop() {} }
const fakeContext = new Proxy({
  createLinearGradient: () => gradient,
  measureText: text => ({ width: Array.from(String(text)).length * 16 }),
  draw: (defer, callback) => callback(),
}, {
  get(target, property) {
    if (property in target) return target[property]
    return () => {}
  },
})

global.wx = {
  getStorageSync: key => storage[key],
  setStorageSync: (key, value) => { storage[key] = value },
  showToast: () => {},
  showShareMenu: () => {},
  navigateTo: () => {},
  navigateBack: () => {},
  switchTab: () => {},
  cloud: {
    callFunction: (options) => {
      const action = options && options.data && options.data.action
      if (cloudFailures.has(action)) return Promise.reject(new Error('offline'))
      const data = Object.prototype.hasOwnProperty.call(cloudResponses, action)
        ? cloudResponses[action]
        : {}
      const result = { result: { ok: true, data } }
      if (options && typeof options.success === 'function') options.success(result)
      return Promise.resolve(result)
    },
  },
  createCanvasContext: () => fakeContext,
  canvasToTempFilePath: (options, page) => {
    canvasOptions = options
    assert.equal(page && typeof page.setData, 'function')
    options.success({ tempFilePath: '/tmp/day-share.png' })
  },
}

function at(value) {
  return new Date(value)
}

function checkCountdown(value, title, units) {
  const countdown = getSchoolCountdown(at(value))
  assert.equal(countdown.title, title)
  assert.deepEqual(countdown.units.map(unit => unit.value), units)
}

function capturePage(pagePath) {
  let definition = null
  global.Page = value => { definition = value }
  delete require.cache[require.resolve(pagePath)]
  require(pagePath)
  assert.ok(definition)
  return definition
}

function createPageInstance(definition) {
  return Object.assign({}, definition, {
    data: JSON.parse(JSON.stringify(definition.data)),
    setData(update, callback) {
      Object.assign(this.data, update)
      if (callback) callback()
    },
  })
}

function read(relative) {
  return fs.readFileSync(path.join(root, relative), 'utf8')
}

async function main() {
  assert.equal(toDateKey(at('2026-11-06T10:00:00+08:00')), '2026-11-06')
  assert.equal(isDateKey('2026-02-29'), false)
  assert.equal(isDateKey('2028-02-29'), true)
  assert.equal(dayDifference('2026-12-01', at('2026-11-06T10:00:00+08:00')), 25)

  checkCountdown('2026-11-06T07:00:00+08:00', '距离上学', ['01', '05', '00'])
  checkCountdown('2026-11-06T08:05:00+08:00', '距离放学', ['07', '15', '00'])
  checkCountdown('2026-11-06T15:19:59+08:00', '距离放学', ['00', '00', '01'])
  checkCountdown('2026-11-06T15:20:00+08:00', '距离周一上学', ['2', '16', '45', '00'])
  checkCountdown('2026-11-07T12:00:00+08:00', '距离周一上学', ['1', '20', '05', '00'])
  checkCountdown('2026-11-08T12:00:00+08:00', '距离周一上学', ['20', '05', '00'])
  console.log('上下学、放学边界与周末倒计时：通过')

  assert.equal(POINTS.vote, 10)
  assert.equal(POINTS.schedule, 5)
  assert.equal(POINTS.nickname, 5)
  assert.equal(MEDAL_NAME, '星耀周冠军')
  assert.equal(weekKey(at('2026-11-07T12:00:00+08:00')), '2026-11-02')
  assert.equal(weekStart(at('2026-11-07T12:00:00+08:00')).getDay(), 1)
  assert.equal(weekKey(previousWeekStart(at('2026-11-07T12:00:00+08:00'))), '2026-10-26')
  assert.equal(sanitizeNickname('  校园达人\n  '), '校园达人')
  const ranked = aggregateRecords([
    { _openid: 'a', points: 10, createdAt: '2026-11-02T01:00:00Z' },
    { _openid: 'b', points: 5, createdAt: '2026-11-02T01:00:00Z' },
    { _openid: 'a', points: 5, createdAt: '2026-11-02T02:00:00Z' },
    { _openid: 'b', points: 10, createdAt: '2026-11-02T03:00:00Z' },
  ])
  assert.deepEqual(ranked.map(item => item.points), [15, 15])
  assert.equal(rankNumber(ranked, 0), 1)
  assert.equal(rankNumber(ranked, 1), 2)
  console.log('达人分、自然周、昵称清理与同分排名：通过')

  writeSchedules([
    { id: 'b', title: '旅行', date: '2026-12-01', note: '保持好状态', createdAt: 2 },
    { id: 'a', title: '考试', date: '2026-11-20', note: '', createdAt: 1 },
  ])
  assert.deepEqual(readSchedules().map(item => item.id), ['a', 'b'])
  const params = new URLSearchParams(buildShareQuery(readSchedules()[0]))
  assert.equal(params.get('title'), '考试')
  assert.equal(params.get('shared'), '1')

  const daysDefinition = capturePage(path.join(root, 'pages/days/index/index.js'))
  const detailDefinition = capturePage(path.join(root, 'pages/day-detail/index/index.js'))
  capturePage(path.join(root, 'pages/message/index/index.js'))
  capturePage(path.join(root, 'pages/index/index.js'))
  capturePage(path.join(root, 'pages/leaderboard/index/index.js'))
  capturePage(path.join(root, 'pages/notifications/index/index.js'))

  let detailUrl = ''
  global.wx.navigateTo = options => { detailUrl = options.url }
  const daysPage = createPageInstance(daysDefinition)
  daysDefinition.goDetail.call(daysPage, { currentTarget: { dataset: { id: 'schedule-a' } } })
  assert.equal(detailUrl, '/pages/day-detail/index/index?id=schedule-a')
  assert.match(read('pages/day-detail/index/index.wxml'), /open-type="share"/)
  assert.match(read('pages/day-detail/index/index.wxml'), /canvas-id="dayShareCanvas"/)
  console.log('日程点击 → Days Matter 分享页 → 原生分享/图片：通过')

  const pageFiles = ['days', 'day-detail', 'message', 'index', 'leaderboard', 'notifications']
  for (const name of pageFiles) {
    const pagePath = name === 'index' ? 'pages/index/index' : `pages/${name}/index/index`
    const definition = capturePage(path.join(root, `${pagePath}.js`))
    const wxml = read(`${pagePath}.wxml`)
    const handlers = Array.from(wxml.matchAll(/(?:bind|catch)(?:tap|input|change|confirm|touchmove)="([^"]+)"/g), match => match[1])
    for (const handler of new Set(handlers)) assert.equal(typeof definition[handler], 'function', `${name}.${handler} 未实现`)
    assert.ok(!/{{[^}]*\.[a-zA-Z]+\(/.test(wxml), `${name} WXML 包含不支持的方法调用`)
    assert.ok(!/<\/?(?:small|strong|b|p)(?:\s|>)/.test(wxml), `${name} 包含非原生 WXML 标签`)
  }
  assert.ok(!/<\/?(?:small|strong|b|p)(?:\s|>)/.test(read('pages/profile/index/index.wxml')))

  const voteDefinition = capturePage(path.join(root, 'pages/vote/detail/detail.js'))
  const voteWxml = read('pages/vote/detail/detail.wxml')
  const voteHandlers = Array.from(voteWxml.matchAll(/(?:bind|catch)tap="([^"]+)"/g), match => match[1])
  for (const handler of new Set(voteHandlers)) assert.equal(typeof voteDefinition[handler], 'function', `vote.${handler} 未实现`)
  assert.ok(!/\{\{[^}]*\b[a-zA-Z_$][\w$]*\s*\(/.test(voteWxml), '投票 WXML 包含不支持的方法调用')
  const votePage = createPageInstance(voteDefinition)
  const votePoll = {
    _id: 'p1', status: 'active', pollType: 'single', hasVoted: false, canChange: true,
    options: [{ optionId: 'o1', label: '一' }, { optionId: 'o2', label: '二' }, { optionId: 'o3', label: '三' }],
  }
  votePage.setData({ poll: votePoll, selectedOptionIds: [] })
  voteDefinition.toggleOption.call(votePage, { currentTarget: { dataset: { id: 'o1' } } })
  assert.equal(votePage.data.optionViews[0].selected, true)
  assert.equal(votePage.data.canSubmit, true)
  votePage.setData({ poll: { ...votePoll, hasVoted: true }, showResults: true, editing: false })
  voteDefinition.startEdit.call(votePage)
  assert.equal(votePage.data.editing, true)
  assert.equal(votePage.data.showResults, false)
  voteDefinition.toggleOption.call(votePage, { currentTarget: { dataset: { id: 'o2' } } })
  assert.deepEqual(votePage.data.selectedOptionIds, ['o2'])
  voteDefinition.cancelEdit.call(votePage)
  assert.equal(votePage.data.showResults, true)
  votePage.setData({ poll: { ...votePoll, pollType: 'multi', maxChoices: 2 }, selectedOptionIds: [] })
  for (const id of ['o1', 'o2', 'o3']) voteDefinition.toggleOption.call(votePage, { currentTarget: { dataset: { id } } })
  assert.deepEqual(votePage.data.selectedOptionIds, ['o1', 'o2'])
  votePage.setData({ poll: { ...votePoll, pollType: 'ranking' }, selectedOptionIds: [] })
  voteDefinition.toggleOption.call(votePage, { currentTarget: { dataset: { id: 'o1' } } })
  assert.equal(votePage.data.canSubmit, false)
  voteDefinition.toggleOption.call(votePage, { currentTarget: { dataset: { id: 'o2' } } })
  assert.equal(votePage.data.canSubmit, true)

  let chartDefinition = null
  global.Component = value => { chartDefinition = value }
  require(path.join(root, 'components/result-chart/index.js'))
  const chart = {
    properties: { results: { total: 2, options: [{ optionId: 'o1', label: '一', count: 3, percent: 60 }] }, pollType: 'multi' },
    setData(update) { Object.assign(this, update) },
  }
  chartDefinition.methods.refresh.call(chart)
  assert.equal(chart.rows[0].percent, 60)
  assert.equal(chart.rows[0].percentText, '60%')
  console.log('投票选中态、改票、选项数量与服务端百分比：通过')

  for (const name of ['days', 'day-detail', 'message', 'index', 'leaderboard']) {
    const pagePath = name === 'index' ? 'pages/index/index' : `pages/${name}/index/index`
    assert.ok(!/display\s*:\s*grid/.test(read(`${pagePath}.wxss`)), `${name} 仍包含兼容性 Grid`)
  }
  assert.match(read('pages/days/index/index.wxss'), /width:\s*14\.2857%/)
  assert.match(read('pages/days/index/index.wxss'), /\.days-view-switch\s*{[^}]*flex-shrink:\s*0/)
  assert.match(read('pages/day-detail/index/index.wxss'), /\.day-detail__actions\s*{[^}]*display:\s*flex/)
  console.log('关键页面事件、WXML 表达式与 Flex 自适应布局：通过')

  const appConfig = JSON.parse(read('app.json'))
  const expectedTabs = [
    'pages/index/index',
    'pages/days/index/index',
    'pages/message/index/index',
    'pages/vote/list/list',
    'pages/profile/index/index',
  ]
  assert.deepEqual(appConfig.tabBar.list.map(tab => tab.pagePath), expectedTabs)
  for (const page of ['pages/day-detail/index/index', 'pages/leaderboard/index/index', 'pages/notifications/index/index']) {
    assert.ok(appConfig.pages.includes(page))
    for (const extension of ['js', 'json', 'wxml', 'wxss']) assert.ok(fs.existsSync(path.join(root, `${page}.${extension}`)))
  }
  assert.ok(!appConfig.tabBar.list.some(tab => tab.pagePath === 'pages/living/index/index'))

  let tabDefinition = null
  global.Component = value => { tabDefinition = value }
  require(path.join(root, 'custom-tab-bar/index.js'))
  assert.deepEqual(tabDefinition.data.list.map(tab => tab.text), ['今日', '日子', '倒计时', '投票', '我的'])
  assert.match(read('pages/index/index.js'), /selected: 0/)
  assert.match(read('pages/days/index/index.js'), /selected: 1/)
  assert.match(read('pages/message/index/index.js'), /selected: 2/)
  assert.match(read('pages/vote/list/list.js'), /selected: 3/)
  assert.match(read('pages/profile/index/index.js'), /selected: 4/)
  assert.ok(!read('pages/index/index.js').includes("call('vote'"))
  assert.ok(!read('pages/index/index.wxml').includes('/pages/vote/'))
  for (const file of ['pages/scan/index/index.js', 'pages/living/index/index.js', 'components/service-notice/index.js']) {
    assert.ok(!read(file).includes("wx.navigateTo({ url: '/pages/vote/list/list' })"))
  }
  console.log('五项 Tab、首页日程优先、投票独立与通知保留：通过')

  const sharedPage = createPageInstance(detailDefinition)
  detailDefinition.onLoad.call(sharedPage, {
    shared: '1',
    title: encodeURIComponent('期末考试'),
    date: '2026-12-01',
    note: encodeURIComponent('认真复习，保持好状态'),
  })
  assert.equal(sharedPage.data.schedule.title, '期末考试')
  assert.equal(sharedPage.data.schedule.note, '认真复习，保持好状态')
  assert.match(detailDefinition.onShareAppMessage.call(sharedPage).path, /shared=1/)
  assert.match(detailDefinition.onShareTimeline.call(sharedPage).query, /title=/)

  const filePath = await createScheduleImage(sharedPage, sharedPage.data.schedule, at('2026-11-06T10:00:00+08:00'))
  assert.equal(filePath, '/tmp/day-share.png')
  assert.equal(canvasOptions.canvasId, 'dayShareCanvas')
  assert.equal(canvasOptions.destWidth, 1080)
  assert.equal(canvasOptions.destHeight, 1350)
  assert.doesNotThrow(() => drawSchedule(fakeContext, sharedPage.data.schedule, at('2026-11-06T10:00:00+08:00')))
  console.log('分享参数独立还原与 1080×1350 Canvas：通过')

  const daysWxml = read('pages/days/index/index.wxml')
  const daysWxss = read('pages/days/index/index.wxss')
  const createWxml = read('pages/day-create/index/index.wxml')
  const createWxss = read('pages/day-create/index/index.wxss')
  assert.ok(appConfig.pages.includes('pages/day-create/index/index'))
  for (const extension of ['js', 'json', 'wxml', 'wxss']) {
    assert.ok(fs.existsSync(path.join(root, `pages/day-create/index/index.${extension}`)))
  }
  assert.ok(!daysWxml.includes('day-form'))
  assert.ok(!daysWxml.includes('formVisible'))
  assert.ok(!daysWxss.includes('day-form'))
  assert.ok(!read('pages/days/index/index.js').includes('formVisible'))
  assert.match(read('pages/days/index/index.js'), /pages\/day-create\/index\/index\?date=/)
  assert.match(read('pages/index/index.js'), /goCreate\(\)/)
  assert.match(read('pages/index/index.wxml'), /bindtap="goCreate"/)
  assert.match(createWxml, /<view class="day-create__submit" bindtap="saveSchedule">保存日子<\/view>/)
  assert.match(createWxml, /bindconfirm="saveSchedule"/)
  assert.ok(!createWxml.includes('<scroll-view'))
  assert.ok(!createWxml.includes('day-form-mask'))
  assert.match(createWxss, /min-height: 100vh/)
  assert.match(createWxss, /\.day-create__submit \{[^}]*min-height: 96rpx/)
  assert.ok(!createWxss.includes('position: fixed'))

  writeSchedules([])
  const createDefinition = capturePage(path.join(root, 'pages/day-create/index/index.js'))
  const createPage = createPageInstance(createDefinition)
  createDefinition.onLoad.call(createPage, { date: '2026-12-01' })
  assert.equal(createPage.data.formDate, '2026-12-01')
  createDefinition.onTitleInput.call(createPage, { detail: { value: '期末考试' } })
  createDefinition.onNoteInput.call(createPage, { detail: { value: '认真复习' } })
  createDefinition.saveSchedule.call(createPage)
  const saved = readSchedules()
  assert.equal(saved.length, 1)
  assert.equal(saved[0].title, '期末考试')
  assert.equal(saved[0].date, '2026-12-01')
  assert.equal(storage['bala.days.lastCreated'], '2026-12-01')
  console.log('添加日子：独立全屏页、确认键可见、保存并回传日期：通过')

  const daysCloudSource = fs.readFileSync(path.resolve(__dirname, '../cloudfunctions/days/index.js'), 'utf8')
  assert.match(daysCloudSource, /doc\(id\)\.set\(/)
  assert.match(daysCloudSource, /const ACTIONS = \{[^}]*list/)
  const daysPageSource = read('pages/days/index/index.js')
  assert.match(daysPageSource, /call\('days', 'list'/)
  assert.match(daysPageSource, /call\('days', 'save'/)
  assert.match(read('pages/day-create/index/index.js'), /queuePendingSchedule/)
  assert.match(read('pages/day-detail/index/index.js'), /addDeletedId/)

  const {
    writePendingSchedules,
    readPendingSchedules,
    queuePendingSchedule,
    addDeletedId,
    migrateLocalSchedules,
    MIGRATED_KEY,
    DELETED_KEY,
  } = require(path.join(root, 'utils/days'))

  delete storage[MIGRATED_KEY]
  writePendingSchedules([])
  writeSchedules([{ id: 'legacy', title: '老日程', date: '2026-11-20', note: '', createdAt: 5 }])
  migrateLocalSchedules()
  assert.ok(readPendingSchedules().some(item => item.id === 'legacy'))
  assert.equal(storage[MIGRATED_KEY], 1)

  writePendingSchedules([])
  storage[DELETED_KEY] = []
  writeSchedules([{ id: 'stale', title: '仅本地残留', date: '2026-11-01', note: '', createdAt: 1 }])
  queuePendingSchedule({ id: 'pending', title: '未同步', date: '2026-12-05', note: '', createdAt: 2 })
  addDeletedId('deleted')
  cloudResponses = {
    list: { list: [
      { id: 'cloudA', title: '云端日程', date: '2026-12-02', note: '另一台设备', createdAt: 3 },
      { id: 'cloudA-dup', title: '云端日程', date: '2026-12-02', note: '另一台设备', createdAt: 3 },
      { id: 'deleted', title: '已删除', date: '2026-12-03', note: '', createdAt: 4 },
    ] },
    save: { schedule: {} },
  }
  const syncDefinition = capturePage(path.join(root, 'pages/days/index/index.js'))
  const syncPage = createPageInstance(syncDefinition)
  syncDefinition.syncMyDays.call(syncPage)
  await new Promise(resolve => setImmediate(resolve))
  const merged = readSchedules()
  assert.ok(merged.some(item => item.id === 'cloudA'), '云端日程应被拉回')
  assert.ok(merged.some(item => item.id === 'pending'), '未同步的新增不应丢失')
  assert.ok(!merged.some(item => item.id === 'cloudA-dup'), '同内容的历史记录应去重')
  assert.ok(!merged.some(item => item.id === 'stale'), '云端已删的本地残留应消失')
  assert.ok(!merged.some(item => item.id === 'deleted'), '墓碑应过滤删除项')
  assert.equal(readPendingSchedules().length, 0, '补传成功后应出队')

  writeSchedules([])
  syncDefinition.syncMyDays.call(syncPage)
  await new Promise(resolve => setImmediate(resolve))
  assert.ok(readSchedules().some(item => item.id === 'cloudA'), '换设备后应恢复云端日程')

  cloudFailures.add('list')
  const offlineBefore = readSchedules()
  syncDefinition.syncMyDays.call(syncPage)
  await new Promise(resolve => setImmediate(resolve))
  assert.deepEqual(readSchedules(), offlineBefore, '离线时不得清空本地日程')
  cloudFailures.delete('list')
  cloudResponses = {}
  console.log('个人日程跨设备云同步：id 对齐、拉回合并、去重、墓碑与离线保护：通过')

  const { normalizeRemoteDays, nextOccurrence } = require(path.join(root, 'utils/remoteDays'))
  const fixedNow = at('2026-11-09T07:00:00+08:00')
  const remoteItems = normalizeRemoteDays({
    events: [
      { _id: 'e1', title: '校园运动会', startAt: '2026-11-12T08:00:00+08:00', location: '操场', status: 'active' },
      { _id: 'e2', title: '已取消活动', startAt: '2026-11-13T08:00:00+08:00', status: 'cancelled' },
    ],
    countdowns: [
      { _id: 'c1', code: 'bus', title: '校车到站', description: '东门', emoji: '🚌', badge: '校车', dailyTime: '07:20', weekdays: [1, 2, 3, 4, 5], isActive: true },
      { _id: 'c2', title: '停用倒计时', dailyTime: '09:00', isActive: false },
    ],
  }, fixedNow)
  assert.equal(remoteItems.length, 2)
  const schoolEvent = remoteItems.find(item => item.source === 'school')
  assert.equal(schoolEvent.title, '校园运动会')
  assert.equal(schoolEvent.date, '2026-11-12')
  assert.equal(schoolEvent.badge, '校历')
  const busItem = remoteItems.find(item => item.source === 'remote')
  assert.equal(busItem.title, '校车到站')
  assert.equal(busItem.date, '2026-11-09')
  assert.equal(new Date(busItem.targetAt).getHours(), 7)
  assert.equal(
    toDateKey(new Date(nextOccurrence({ dailyTime: '07:20', weekdays: [1, 2, 3, 4, 5] }, at('2026-11-06T20:00:00+08:00')))),
    '2026-11-09',
  )
  assert.match(read('pages/days/index/index.js'), /loadRemoteDays/)
  assert.match(read('pages/message/index/index.js'), /loadRemoteDays/)
  assert.match(read('pages/days/index/index.wxml'), /data-source="\{\{item.source\}\}"/)
  assert.match(read('pages/message/index/index.wxml'), /bindtap="openFullscreen"/)
  console.log('远程校历活动与可配置校车倒计时（含周末顺延）：通过')

  assert.ok(appConfig.pages.includes('pages/countdown-detail/index/index'))
  const countdownPage = capturePage(path.join(root, 'pages/countdown-detail/index/index.js'))
  const fullPage = createPageInstance(countdownPage)
  countdownPage.onLoad.call(fullPage, {
    shared: '1',
    title: encodeURIComponent('校车到站'),
    date: '2026-11-09',
    targetAt: encodeURIComponent('2026-11-09T07:20:00+08:00'),
    emoji: encodeURIComponent('🚌'),
  })
  assert.equal(fullPage.data.item.title, '校车到站')
  assert.equal(fullPage.data.item.badge, '倒计时')
  assert.match(countdownPage.onShareAppMessage.call(fullPage).path, /shared=1/)
  assert.match(buildCountdownQuery(fullPage.data.item), /targetAt=/)
  assert.equal(countdownUnits(fullPage.data.item.targetAt, fixedNow).minutes, '20')
  assert.doesNotThrow(() => drawCountdown(fakeContext, fullPage.data.item, fixedNow))
  assert.doesNotThrow(() => drawBrandHeader(fakeContext))
  assert.equal(await createCountdownImage(fullPage, fullPage.data.item, fixedNow), '/tmp/day-share.png')
  assert.equal(canvasOptions.destWidth, 1080)
  assert.equal(canvasOptions.destHeight, 1350)
  console.log('倒计时全屏页：秒级刷新、原生转发与 1080×1350 分享图：通过')

  const webRead = relative => fs.readFileSync(path.resolve(__dirname, '../../bala-web', relative), 'utf8')
  const serverRead = relative => fs.readFileSync(path.resolve(__dirname, '../server', relative), 'utf8')
  for (const target of ['pages/day-detail/index/index.wxml', 'pages/countdown-detail/index/index.wxml']) {
    assert.match(read(target), /叭啦·过日子/)
    assert.match(read(target), /logo-mark\.png/)
    assert.match(read(target), /show-menu-by-longpress/)
  }
  assert.match(read('pages/index/index.wxml'), /home-topbar__logo/)
  assert.ok(!read('pages/index/index.wxml').includes('把时间和精力，留给真正重要的日子'))
  assert.match(read('utils/dayShare.js'), /drawBrandHeader/)
  assert.match(read('utils/dayShare.js'), /loadBrandLogo/)
  assert.match(webRead('src/pages/DayDetail.tsx'), /叭啦·过日子/)
  assert.match(webRead('src/utils/dayShare.ts'), /叭啦·过日子/)
  assert.match(webRead('src/styles/days.css'), /\.day-share-card__brand/)
  assert.match(webRead('src/pages/DayDetail.tsx'), /day-share-preview/)
  assert.match(serverRead('app/services/web_service.py'), /"remote"/)
  assert.match(serverRead('app/repository/local_repo.py'), /days_remote/)
  assert.match(serverRead('app/services/content_service.py'), /remote_countdowns/)
  assert.match(fs.readFileSync(path.resolve(__dirname, '../cloudfunctions/days/index.js'), 'utf8'), /remote/)
  console.log('全端分享品牌页脚与远程数据服务端契约：通过')

  // ── 网页端 ↔ 小程序绑定码互通 ──
  assert.ok(appConfig.pages.includes('pages/bind/index/index'))
  for (const extension of ['js', 'json', 'wxml', 'wxss']) {
    assert.ok(fs.existsSync(path.join(root, `pages/bind/index/index.${extension}`)))
  }
  assert.match(read('pages/profile/index/index.wxml'), /bindtap="goBind"/)
  assert.match(read('pages/profile/index/index.js'), /pages\/bind\/index\/index/)
  const identityCloud = fs.readFileSync(path.resolve(__dirname, '../cloudfunctions/identity/index.js'), 'utf8')
  assert.match(identityCloud, /issueBindCode/)
  assert.match(identityCloud, /bind_codes/)
  assert.match(identityCloud, /identity_links/)
  assert.match(identityCloud, /const ACTIONS = \{ get, issueBindCode \}/)
  for (const fn of ['vote', 'club', 'event', 'scan', 'me', 'analytics', 'leaderboard', 'days']) {
    const source = fs.readFileSync(path.resolve(__dirname, `../cloudfunctions/${fn}/index.js`), 'utf8')
    assert.match(source, /indexOf\('linked:'\) === 0/, `${fn} 应识别绑定身份`)
  }
  assert.match(serverRead('app/services/identity_link.py'), /async def resolve/)
  assert.match(serverRead('app/services/identity_link.py'), /async def bind/)
  assert.match(serverRead('app/services/web_service.py'), /identity_link\.resolve/)
  assert.match(serverRead('app/api/v1/web.py'), /\/session\/bind/)
  assert.match(serverRead('app/api/v1/web.py'), /\/session\/link/)
  assert.match(serverRead('app/repository/local_repo.py'), /startswith\("linked:"\)/)
  assert.match(webRead('src/utils/identity.ts'), /bindAccount/)
  assert.match(webRead('src/pages/Profile.tsx'), /账号互通/)

  const bindDefinition = capturePage(path.join(root, 'pages/bind/index/index.js'))
  const bindPage = createPageInstance(bindDefinition)
  cloudResponses = { issueBindCode: { code: '123456', expiresIn: 600 } }
  await bindDefinition.issueCode.call(bindPage)
  assert.equal(bindPage.data.rawCode, '123456')
  assert.equal(bindPage.data.codeText, '1 2 3 4 5 6')
  assert.equal(bindPage.data.secondsLeft, 600)
  bindDefinition.clearTimer.call(bindPage)
  cloudResponses = {}
  console.log('网页端 ↔ 小程序绑定码互通：签发、校验、身份注入与两端入口：通过')

  console.log('全部需求相关自动检查通过')
}

main().catch(error => {
  console.error(error)
  process.exitCode = 1
})
