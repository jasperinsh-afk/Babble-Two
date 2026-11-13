const { call } = require('../../../utils/api')
const { withShare } = require('../../../utils/share')

Page(withShare({
  data: {
    loading: true,
    weekKey: '',
    list: [],
    my: { nickname: '同学', totalPoints: 0, currentWeekPoints: 0, rank: 0, champions: [] },
    rules: [],
    editing: false,
    nickname: '',
    saving: false,
    error: '',
  },

  onShow() {
    const tabBar = this.getTabBar?.()
    if (tabBar) tabBar.setData({ selected: -1 })
    this.loadLeaderboard()
  },

  async onPullDownRefresh() {
    await this.loadLeaderboard()
    wx.stopPullDownRefresh()
  },

  async loadLeaderboard() {
    this.setData({ loading: true })
    try {
      const data = await call('leaderboard', 'weekly')
      this.setData({
        weekKey: data.weekKey,
        list: data.list || [],
        my: data.my || this.data.my,
        rules: data.rules || [],
      })
    } catch (error) {
      console.warn('[leaderboard] 加载失败', error)
    } finally {
      this.setData({ loading: false })
    }
  },

  openNickname() {
    this.setData({
      editing: true,
      nickname: this.data.my.nicknameSet ? this.data.my.nickname : '',
      error: '',
    })
  },

  closeNickname() {
    if (!this.data.saving) this.setData({ editing: false, error: '' })
  },

  onNicknameInput(event) {
    this.setData({ nickname: event.detail.value, error: '' })
  },

  async saveNickname() {
    const nickname = this.data.nickname.trim()
    if (Array.from(nickname).length < 2) {
      this.setData({ error: '昵称至少需要 2 个字符' })
      return
    }
    this.setData({ saving: true, error: '' })
    try {
      await call('leaderboard', 'setNickname', { nickname })
      this.setData({ editing: false })
      wx.showToast({ title: '昵称已保存', icon: 'success' })
      await this.loadLeaderboard()
    } catch (error) {
      this.setData({ error: error.message || '保存失败，请重试' })
    } finally {
      this.setData({ saving: false })
    }
  },

  noop() {},
}, {
  title: '本周达人榜，看看谁是星耀周冠军',
  path: '/pages/leaderboard/index/index',
  query: '',
}))
