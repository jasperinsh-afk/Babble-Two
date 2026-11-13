const {
  toDateKey,
  isDateKey,
  readSchedules,
  writeSchedules,
  createScheduleId,
  queuePendingSchedule,
  removePendingSchedule,
  LAST_CREATED_KEY,
} = require('../../../utils/days')
const { call } = require('../../../utils/api')

Page({
  data: {
    formTitle: '',
    formDate: '',
    formNote: '',
    formError: '',
    saving: false,
  },

  onLoad(options) {
    const date = options && isDateKey(options.date) ? options.date : toDateKey(new Date())
    this.setData({ formDate: date })
  },

  onTitleInput(event) {
    this.setData({ formTitle: event.detail.value, formError: '' })
  },

  onDateChange(event) {
    this.setData({ formDate: event.detail.value, formError: '' })
  },

  onNoteInput(event) {
    this.setData({ formNote: event.detail.value })
  },

  saveSchedule() {
    if (this.data.saving) return
    const title = String(this.data.formTitle || '').trim()
    const date = this.data.formDate
    if (!title) {
      this.setData({ formError: '给这个日子起一个名字吧' })
      return
    }
    if (!isDateKey(date)) {
      this.setData({ formError: '请选择有效日期' })
      return
    }
    const schedule = {
      id: createScheduleId(),
      title,
      date,
      note: String(this.data.formNote || '').trim(),
      createdAt: Date.now(),
    }
    try {
      writeSchedules(readSchedules().concat(schedule))
      queuePendingSchedule(schedule)
      wx.setStorageSync(LAST_CREATED_KEY, date)
      this.setData({ saving: true, formError: '' })
      wx.showToast({ title: '日子已保存', icon: 'success' })
      call('days', 'save', {
        id: schedule.id,
        title: schedule.title,
        date: schedule.date,
        note: schedule.note,
        createdAt: schedule.createdAt,
      }, { silent: true, noRetry: true })
        .then(() => removePendingSchedule(schedule.id))
        .catch(() => {})
      call('leaderboard', 'track', {
        type: 'schedule:create', scheduleId: schedule.id,
      }, { silent: true, noRetry: true }).catch(() => {})
      wx.navigateBack({ fail: () => wx.switchTab({ url: '/pages/days/index/index' }) })
    } catch (error) {
      console.error('[day-create] 保存日程失败', error)
      this.setData({ formError: '保存失败，请检查存储权限后重试', saving: false })
    }
  },
})
