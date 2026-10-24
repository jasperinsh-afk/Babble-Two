const { call } = require('../../utils/api')

Component({
  options: {
    styleIsolation: 'apply-shared',
  },
  data: {
    keyword: '',
    currentCategory: 'all',
    tabs: [
      { category: 'all', label: '全部' },
      { category: 'academic', label: '学术' },
      { category: 'sports', label: '体育' },
      { category: 'art', label: '艺术' },
      { category: 'charity', label: '公益' },
      { category: 'interest', label: '兴趣' },
    ],
    clubs: [],
    page: 0,
    hasMore: true,
    loading: false,
  },

  lifetimes: {
    attached() {
      this.loadClubs()
    },
  },

  methods: {
    onInput(e) {
      this.setData({ keyword: e.detail.value })
    },

    doSearch() {
      this.setData({ page: 0, clubs: [], hasMore: true }, () => this.loadClubs())
    },

    switchCategory(e) {
      const category = e.currentTarget.dataset.category
      this.setData({ currentCategory: category, page: 0, clubs: [], hasMore: true }, () =>
        this.loadClubs()
      )
    },

    async loadClubs() {
      if (this.data.loading) return
      this.setData({ loading: true })
      try {
        const res = await call('club', 'list', {
          category: this.data.currentCategory,
          keyword: this.data.keyword,
          page: this.data.page,
        })
        this.setData({
          clubs: [...this.data.clubs, ...(res.list || [])],
          hasMore: !!res.hasMore,
          page: this.data.page + 1,
        })
      } catch (e) {
        /* api.js 已弹 toast */
      } finally {
        this.setData({ loading: false })
      }
    },

    reload() {
      this.setData({ page: 0, clubs: [], hasMore: true }, () => this.loadClubs())
    },

    loadMore() {
      if (!this.data.hasMore || this.data.loading) return
      this.loadClubs()
    },

    goDetail(e) {
      wx.navigateTo({ url: `/pages/club/detail/detail?id=${e.currentTarget.dataset.id}` })
    },
  },
})
