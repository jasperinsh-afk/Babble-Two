const { call } = require('../../../utils/api')
const { pollTypeLabel, pollTagLabel } = require('../../../utils/config')
const { countdownText } = require('../../../utils/format')
const { pushFootprint } = require('../../../utils/storage')

Page({
  data: {
    pollId: '',
    poll: null,
    typeText: '',
    tagText: '',
    timeText: '',
    selectedOptionIds: [],
    results: null,
    showResults: false,
    submitting: false,
  },

  onLoad(options) {
    const id = options.id
    if (!id) {
      wx.showToast({ title: '缺少投票 ID', icon: 'none' })
      wx.navigateBack()
      return
    }
    this.setData({ pollId: id }, () => this.load())
  },

  async load() {
    try {
      const poll = await call('vote', 'detail', { pollId: this.data.pollId })
      const typeText = pollTypeLabel[poll.pollType] || '投票'
      const tagText = pollTagLabel[poll.tag] || poll.tag || ''
      const timeText = poll.endAt ? `截止 ${countdownText(poll.endAt)}` : ''
      const chainPercent =
        poll.pollType === 'groupbuy' && poll.maxParticipants
          ? Math.min(100, Math.round(((poll.participantCount || 0) / poll.maxParticipants) * 100))
          : 0

      this.setData({
        poll,
        typeText,
        tagText,
        timeText,
        chainPercent,
        selectedOptionIds: poll.myChoice || [],
        showResults: poll.pollType !== 'groupbuy' && poll.hasVoted,
      })

      if (poll.hasVoted && poll.pollType !== 'groupbuy') {
        this.loadResults()
      }
    } catch (e) {
      wx.showToast({ title: '加载失败', icon: 'none' })
    }
  },

  isSelected(id) {
    return this.data.selectedOptionIds.indexOf(id) >= 0
  },

  toggleOption(e) {
    const id = e.currentTarget.dataset.id
    const { poll, selectedOptionIds } = this.data
    if (!poll || poll.hasVoted || poll.status !== 'active') return

    if (poll.pollType === 'single' || poll.pollType === 'pk' || poll.pollType === 'groupbuy') {
      this.setData({ selectedOptionIds: [id] })
      return
    }

    const idx = selectedOptionIds.indexOf(id)
    if (idx >= 0) {
      selectedOptionIds.splice(idx, 1)
    } else {
      if (poll.maxChoices && selectedOptionIds.length >= poll.maxChoices) {
        wx.showToast({ title: `最多选 ${poll.maxChoices} 项`, icon: 'none' })
        return
      }
      selectedOptionIds.push(id)
    }
    this.setData({ selectedOptionIds: [...selectedOptionIds] })
  },

  async submitVote() {
    const { poll, selectedOptionIds } = this.data
    if (!selectedOptionIds.length) {
      wx.showToast({ title: '请选择选项', icon: 'none' })
      return
    }
    if (poll.pollType === 'multi' && poll.maxChoices && selectedOptionIds.length > poll.maxChoices) {
      wx.showToast({ title: `最多选 ${poll.maxChoices} 项`, icon: 'none' })
      return
    }

    this.setData({ submitting: true })
    try {
      await call('vote', 'cast', { pollId: poll._id, optionIds: selectedOptionIds }, { loading: '提交中…' })
      wx.showToast({ title: '投票成功', icon: 'success' })
      pushFootprint({ pollId: poll._id, title: poll.title, at: new Date() })
      await this.load()
    } catch (e) {
      /* api.js 已弹 toast */
    } finally {
      this.setData({ submitting: false })
    }
  },

  async loadResults() {
    try {
      const results = await call('vote', 'results', { pollId: this.data.pollId })
      this.setData({ results })
    } catch (e) {
      /* ignore */
    }
  },

  async joinChain() {
    const { poll, selectedOptionIds } = this.data
    if (!selectedOptionIds.length) {
      wx.showToast({ title: '请选择接龙时间段', icon: 'none' })
      return
    }
    this.setData({ submitting: true })
    try {
      await call('vote', 'joinChain', { pollId: poll._id, optionId: selectedOptionIds[0] })
      wx.showToast({ title: '接龙成功', icon: 'success' })
      await this.load()
    } finally {
      this.setData({ submitting: false })
    }
  },

  async leaveChain() {
    this.setData({ submitting: true })
    try {
      await call('vote', 'leaveChain', { pollId: this.data.pollId })
      wx.showToast({ title: '已取消', icon: 'success' })
      await this.load()
    } finally {
      this.setData({ submitting: false })
    }
  },

  onShareAppMessage() {
    const { poll, pollId } = this.data
    const title = poll && poll.title ? clip(poll.title) : '这个投票，你会怎么选？'
    return {
      title,
      path: `/pages/vote/detail/detail?id=${pollId}`,
      imageUrl: '/assets/brand/share-card.png',
    }
  },
})

// 分享标题截断：超长话题名折叠，保证卡片一行可读
function clip(title) {
  return title.length > 18 ? `${title.slice(0, 18)}…` : title
}
