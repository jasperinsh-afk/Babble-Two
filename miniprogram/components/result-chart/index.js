Component({
  properties: {
    results: { type: Object, value: {} },
    pollType: { type: String, value: 'single' },
  },
  data: {
    isPk: false,
    rows: [],
    leftPercent: 0,
    rightPercent: 0,
  },
  lifetimes: {
    attached() {
      this.refresh()
    },
  },
  observers: {
    'results': function () {
      this.refresh()
    },
  },
  methods: {
    refresh() {
      const { results, pollType } = this.properties
      const options = (results && results.options) || []
      const total = (results && results.total) || 0

      const rows = options.map((o) => ({
        optionId: o.optionId,
        label: o.label,
        count: o.count || 0,
        percent: total ? Math.round(((o.count || 0) / total) * 1000) / 10 : 0,
        percentText: total ? `${Math.round(((o.count || 0) / total) * 100)}%` : '0%',
      }))

      const isPk = pollType === 'pk' && rows.length === 2
      this.setData({ rows, isPk })

      if (isPk) {
        // 延迟触发宽度动画
        setTimeout(() => {
          this.setData({
            leftPercent: rows[0].percent,
            rightPercent: rows[1].percent,
          })
        }, 20)
      }
    },
  },
})
