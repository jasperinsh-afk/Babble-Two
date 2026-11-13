/**
 * 「校区尚未开通该服务」底部弹层
 *
 * 用法：页面 json 注册组件后
 *   <service-notice show="{{noticeShow}}" label="{{noticeLabel}}" bind:close="onNoticeClose" />
 */
Component({
  options: {
    // 复用页面的 .btn 等全局样式
    styleIsolation: 'apply-shared',
  },

  properties: {
    show: { type: Boolean, value: false },
    // 未开通的服务名，如「扫码打卡」
    label: { type: String, value: '' },
  },

  methods: {
    onClose() {
      this.triggerEvent('close')
    },

    onMaskTap() {
      this.triggerEvent('close')
    },

    noop() {},

    goVote() {
      this.triggerEvent('close')
      wx.switchTab({ url: '/pages/vote/list/list' })
    },
  },
})
