const { call } = require('../../../utils/api')
const { clubCategoryLabel } = require('../../../utils/config')

Page({
  data: {
    clubId: '',
    club: null,
    posts: [],
    loading: false,
    initial: '',
    categoryText: '',
  },

  onLoad(options) {
    const id = options.id
    if (!id) {
      wx.showToast({ title: '缺少社团 ID', icon: 'none' })
      wx.navigateBack()
      return
    }
    this.setData({ clubId: id }, () => this.load())
  },

  async load() {
    this.setData({ loading: true })
    try {
      const [club, posts] = await Promise.all([
        call('club', 'detail', { clubId: this.data.clubId }),
        call('club', 'posts', { clubId: this.data.clubId }),
      ])
      this.setData({
        club,
        posts: posts.list || [],
        initial: (club.name || '社').charAt(0),
        categoryText: clubCategoryLabel[club.category] || club.category,
      })
    } catch (e) {
      console.warn('[club/detail] 加载失败', e)
    } finally {
      this.setData({ loading: false })
    }
  },

  async toggleJoin() {
    const { club, clubId } = this.data
    if (!club) return
    const action = club.joined ? 'leave' : 'join'
    try {
      await call('club', action, { clubId })
      wx.showToast({ title: club.joined ? '已退出' : '已加入', icon: 'success' })
      this.setData({ 'club.joined': !club.joined })
      // 简单刷新计数
      this.load()
    } catch (e) {
      /* api.js 已弹 toast */
    }
  },

  onShareAppMessage() {
    const { club, clubId } = this.data
    const name = club && club.name ? club.name : ''
    return {
      title: name ? `${name} · 欢迎来看看` : '发现一个不错的社团',
      path: `/pages/club/detail/detail?id=${clubId}`,
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})
