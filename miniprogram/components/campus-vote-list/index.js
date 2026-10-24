const { call } = require('../../utils/api')

Component({
  options: {
    styleIsolation: 'apply-shared',
  },
  data: {
    currentTag: 'all',
    tabs: [
      { tag: 'all', label: '全部' },
      { tag: 'news', label: '时事' },
      { tag: 'campus', label: '学习' },
      { tag: 'meme', label: '热梗' },
      { tag: 'group', label: '接龙' },
    ],
    polls: [],
    page: 0,
    hasMore: true,
    loading: false,
  },

  lifetimes: {
    attached() {
      this.loadPolls()
    },
  },

  methods: {
    switchTag(e) {
      const tag = e.currentTarget.dataset.tag
      this.setData({ currentTag: tag, page: 0, polls: [], hasMore: true }, () => this.loadPolls())
    },

    async loadPolls() {
      if (this.data.loading) return
      this.setData({ loading: true })

      try {
        const res = await call('vote', 'list', {
          tag: this.data.currentTag,
          page: this.data.page,
        })
        this.setData({
          polls: [...this.data.polls, ...(res.list || [])],
          hasMore: !!res.hasMore,
          page: this.data.page + 1,
        })
      } catch (e) {
        /* toast 已由 api.js 处理 */
      } finally {
        this.setData({ loading: false })
      }
    },

    reload() {
      this.setData({ page: 0, polls: [], hasMore: true }, () => this.loadPolls())
    },

    loadMore() {
      if (!this.data.hasMore || this.data.loading) return
      this.loadPolls()
    },

    goDetail(e) {
      wx.navigateTo({ url: `/pages/vote/detail/detail?id=${e.currentTarget.dataset.id}` })
    },
  },
})
