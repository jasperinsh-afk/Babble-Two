Component({
  properties: {
    title: { type: String, value: '' },
    actionText: { type: String, value: '' },
  },
  methods: {
    onTap() {
      this.triggerEvent('action')
    },
  },
})
