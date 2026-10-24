const { clubCategoryLabel } = require('../../utils/config')

Component({
  properties: {
    club: { type: Object, value: {} },
  },
  data: {
    categoryText: '',
  },
  lifetimes: {
    attached() {
      const club = this.properties.club
      this.setData({
        categoryText: clubCategoryLabel[club.category] || club.category,
        initial: (club.name || '社').charAt(0),
      })
    },
  },
  methods: {
    onTap() {
      this.triggerEvent('tap')
    },
  },
})
