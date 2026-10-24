const { pollTypeLabel, pollTagLabel } = require('../../utils/config')
const { countdownText, compactNumber } = require('../../utils/format')

Component({
  properties: {
    poll: { type: Object, value: {} },
  },
  data: {
    typeText: '',
    tagText: '',
    totalText: '',
    timeText: '',
    joinPercent: 0,
    joinText: '',
  },
  lifetimes: {
    attached() {
      const { poll } = this.properties
      const total = poll.totalVotes || 0
      this.setData({
        typeText: pollTypeLabel[poll.pollType] || '投票',
        tagText: pollTagLabel[poll.tag] || poll.tag || '',
        totalText: `${compactNumber(total)} 已投`,
        timeText: poll.endAt ? `剩 ${countdownText(poll.endAt)}` : '',
        joinPercent:
          poll.pollType === 'groupbuy' && poll.maxParticipants
            ? Math.min(100, Math.round(((poll.participantCount || 0) / poll.maxParticipants) * 100))
            : 0,
        joinText:
          poll.pollType === 'groupbuy'
            ? `${poll.participantCount || 0}/${poll.maxParticipants || '∞'}`
            : '',
      })
    },
  },
  methods: {
    onTap() {
      this.triggerEvent('tap')
    },
  },
})
