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

      const rows = options.map((o) => {
        const fallback = total ? ((o.count || 0) / total) * 100 : 0
        const value = Number(o.percent)
        const percent = Math.max(0, Math.min(100, Number.isFinite(value) ? value : fallback))
        return {
          optionId: o.optionId,
          label: o.label,
          count: o.count || 0,
          percent,
          percentText: `${Math.round(percent)}%`,
        }
      })

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
