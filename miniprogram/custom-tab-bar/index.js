Component({
  data: {
    selected: 0,
    list: [
      {
        pagePath: '/pages/index/index',
        iconPath: '/assets/tabbar/home.png',
        selectedIconPath: '/assets/tabbar/home_active.png',
        text: '今日',
      },
      {
        pagePath: '/pages/campus/index/index',
        iconPath: '/assets/tabbar/campus.png',
        selectedIconPath: '/assets/tabbar/campus_active.png',
        text: '校园',
      },
      {
        pagePath: '/pages/message/index/index',
        iconPath: '/assets/tabbar/message.png',
        selectedIconPath: '/assets/tabbar/message_active.png',
        text: '消息',
      },
      {
        pagePath: '/pages/profile/index/index',
        iconPath: '/assets/tabbar/profile.png',
        selectedIconPath: '/assets/tabbar/profile_active.png',
        text: '我的',
      },
    ],
  },

  methods: {
    switchTab(e) {
      const { path, index } = e.currentTarget.dataset
      if (this.data.selected === index) return
      wx.switchTab({ url: path })
    },
  },
})
