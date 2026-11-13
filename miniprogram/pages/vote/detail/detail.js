const { call } = require('../../../utils/api')
const { pollTypeLabel, pollTagLabel } = require('../../../utils/config')
const { countdownText } = require('../../../utils/format')
const { pushFootprint } = require('../../../utils/storage')

const { withShare } = require('../../../utils/share')

const SINGLE_TYPES = ['single', 'pk', 'groupbuy']

function choiceRange(poll) {
  if (!poll) return [0, 0]
  if (poll.pollType === 'ranking') return [2, Math.min(poll.maxChoices || 6, 6)]
  if (poll.pollType === 'multi') return [1, Math.min(poll.maxChoices || 8, 8)]
  return [1, 1]
}

function selectionData(poll, selectedOptionIds, submitting = false) {
  const [minChoices, maxChoices] = choiceRange(poll)
  const selectable = poll && poll.status === 'active' && (!poll.hasVoted || poll.canChange)
  const validCount = selectedOptionIds.length >= minChoices && selectedOptionIds.length <= maxChoices
  return {
    optionViews: ((poll && poll.options) || []).map(option => ({
      ...option,
      selected: selectedOptionIds.includes(option.optionId),
    })),
    canSubmit: Boolean(selectable && validCount && !submitting),
  }
}

Page(withShare({
  data: {
    pollId: '',
    poll: null,
    typeText: '',
    tagText: '',
    timeText: '',
    selectedOptionIds: [],
    optionViews: [],
    isSingleLike: true,
    canSubmit: false,
    editing: false,
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

      const selectedOptionIds = Array.isArray(poll.myChoice) ? poll.myChoice : []
      this.setData({
        poll,
        typeText,
        tagText,
        timeText,
        chainPercent,
        selectedOptionIds,
        isSingleLike: SINGLE_TYPES.includes(poll.pollType),
        showResults: poll.pollType !== 'groupbuy' && poll.hasVoted,
        editing: false,
        ...selectionData(poll, selectedOptionIds),
      })

      if (poll.hasVoted && poll.pollType !== 'groupbuy') {
        this.loadResults()
      }
    } catch (e) {
      console.warn('[vote/detail] 加载失败', e)
    }
  },

  startEdit() {
    const { poll, selectedOptionIds } = this.data
    if (!poll || !poll.canChange) return
    this.setData({ editing: true, showResults: false, ...selectionData(poll, selectedOptionIds) })
  },

  cancelEdit() {
    this.setData({ editing: false, showResults: Boolean(this.data.poll && this.data.poll.hasVoted) })
  },

  toggleOption(e) {
    const id = e.currentTarget.dataset.id
    const { poll, selectedOptionIds } = this.data
    if (!poll || poll.status !== 'active') return
    if (poll.hasVoted && (poll.pollType === 'groupbuy' || !poll.canChange || !this.data.editing)) return

    if (SINGLE_TYPES.includes(poll.pollType)) {
      const next = [id]
      this.setData({ selectedOptionIds: next, ...selectionData(poll, next) })
      return
    }

    const next = [...selectedOptionIds]
    const idx = next.indexOf(id)
    if (idx >= 0) {
      next.splice(idx, 1)
    } else {
      const [, maxChoices] = choiceRange(poll)
      if (next.length >= maxChoices) {
        wx.showToast({ title: `最多选 ${maxChoices} 项`, icon: 'none' })
        return
      }
      next.push(id)
    }
    this.setData({ selectedOptionIds: next, ...selectionData(poll, next) })
  },

  async submitVote() {
    const { poll, selectedOptionIds } = this.data
    if (!poll || this.data.submitting || poll.status !== 'active') return
    if (poll.hasVoted && (!poll.canChange || !this.data.editing)) return
    const [minChoices, maxChoices] = choiceRange(poll)
    if (selectedOptionIds.length < minChoices) {
      wx.showToast({ title: minChoices > 1 ? `请至少选 ${minChoices} 项` : '请选择选项', icon: 'none' })
      return
    }
    if (selectedOptionIds.length > maxChoices) {
      wx.showToast({ title: `最多选 ${maxChoices} 项`, icon: 'none' })
      return
    }

    this.setData({ submitting: true, canSubmit: false })
    try {
      await call('vote', 'cast', { pollId: poll._id, optionIds: selectedOptionIds }, { loading: '提交中…' })
      wx.showToast({ title: poll.hasVoted ? '投票已修改' : '投票成功', icon: 'success' })
      pushFootprint({ pollId: poll._id, title: poll.title, at: new Date() })
      await this.load()
    } catch (e) {
      wx.showToast({ title: e && e.message ? e.message : '提交失败，请重试', icon: 'none' })
    } finally {
      this.setData({ submitting: false, ...selectionData(poll, selectedOptionIds) })
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
    const title = poll && poll.title ? clip(poll.title) : '叭啦·投票'
    return {
      title,
      path: `/pages/vote/detail/detail?id=${pollId}`,
      imageUrl: '/assets/brand/share-card.png',
    }
  },
}))

// 分享标题截断：超长话题名折叠，保证卡片一行可读
function clip(title) {
  return title.length > 18 ? `${title.slice(0, 18)}…` : title
}
