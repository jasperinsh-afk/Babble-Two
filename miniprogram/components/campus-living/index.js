const { call } = require('../../utils/api')
const { priceText } = require('../../utils/format')

Component({
  options: {
    styleIsolation: 'apply-shared',
  },
  data: {
    currentTab: 0,
    channels: [],
    currentChannel: '',
    dormPosts: [],
    lostKind: 'all',
    lostItems: [],
    secondItems: [],
    loading: false,
  },

  lifetimes: {
    attached() {
      this.loadDormChannels()
      this.loadLostFound()
      this.loadSecondHand()
    },
  },

  methods: {
    switchTab(e) {
      const idx = Number(e.currentTarget.dataset.idx)
      this.setData({ currentTab: idx })
    },

    async loadDormChannels() {
      try {
        const res = await call('living', 'channels')
        const channels = res.list || []
        this.setData({ channels })
        if (channels.length && !this.data.currentChannel) {
          this.setData({ currentChannel: channels[0]._id }, () => this.loadDormPosts())
        }
      } catch (e) {
        wx.showToast({ title: '频道加载失败', icon: 'none' })
      }
    },

    async loadDormPosts() {
      if (!this.data.currentChannel) return
      this.setData({ loading: true })
      try {
        const res = await call('living', 'channelPosts', { channelId: this.data.currentChannel })
        this.setData({ dormPosts: res.list || [] })
      } catch (e) {
        wx.showToast({ title: '帖子加载失败', icon: 'none' })
      } finally {
        this.setData({ loading: false })
      }
    },

    selectChannel(e) {
      const id = e.currentTarget.dataset.id
      this.setData({ currentChannel: id }, () => this.loadDormPosts())
    },

    async loadLostFound() {
      this.setData({ loading: true })
      try {
        const res = await call('living', 'lostFound', { kind: this.data.lostKind })
        this.setData({ lostItems: res.list || [] })
      } catch (e) {
        wx.showToast({ title: '失物招领加载失败', icon: 'none' })
      } finally {
        this.setData({ loading: false })
      }
    },

    async loadSecondHand() {
      this.setData({ loading: true })
      try {
        const res = await call('living', 'secondHand')
        this.setData({ secondItems: res.list || [] })
      } catch (e) {
        wx.showToast({ title: '二手交换加载失败', icon: 'none' })
      } finally {
        this.setData({ loading: false })
      }
    },

    setLostKind(e) {
      const kind = e.currentTarget.dataset.kind
      this.setData({ lostKind: kind }, () => this.loadLostFound())
    },

    reload() {
      this.loadDormChannels()
      this.loadLostFound()
      this.loadSecondHand()
    },

    priceText,
  },
})
