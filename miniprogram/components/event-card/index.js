const { dateTimeText, countdownText } = require('../../utils/format')

Component({
  properties: {
    event: { type: Object, value: {} },
  },
  data: {
    initial: '',
    timeText: '',
    countText: '',
  },
  lifetimes: {
    attached() {
      const e = this.properties.event
      const endAt = e.endAt || e.startAt
      this.setData({
        initial: (e.title || '活').charAt(0),
        timeText: e.startAt ? `${dateTimeText(e.startAt)} · ${countdownText(endAt)}` : '',
        countText: e.maxParticipants
          ? `${e.participantCount || 0}/${e.maxParticipants} 报名`
          : `${e.participantCount || 0} 人已报名`,
      })
    },
  },
  methods: {
    onTap() {
      this.triggerEvent('tap')
    },
  },
})
