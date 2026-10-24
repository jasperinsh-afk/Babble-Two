Component({
  properties: {
    icon: { type: String, value: '📭' },
    title: { type: String, value: '暂无内容' },
    subtitle: { type: String, value: '' },
    actionText: { type: String, value: '' },
  },
  methods: {
    onTap() {
      this.triggerEvent('action')
    },
  },
})
