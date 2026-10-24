/**
 * 云函数统一调用封装
 *
 * 全站所有网络请求必须经过本文件，页面禁止直接调用 wx.cloud.callFunction。
 * 统一处理：loading 遮罩、失败 toast、超时重试一次、{ok,data,message} 解包。
 */

/** 合并中的同名请求：避免快速重复点击打出多个云调用 */
const inflight = new Map()

function toast(message) {
  wx.showToast({ title: message || '网络异常', icon: 'none', duration: 2000 })
}

/**
 * @param {string} name    云函数名
 * @param {string} action  操作
 * @param {object} payload 参数
 * @param {object} opts    { loading: 文案|false, silent: 不弹 toast, noRetry, dedupe }
 * @returns {Promise<any>} 成功时返回 data
 */
function call(name, action, payload = {}, opts = {}) {
  const { loading = '', silent = false, noRetry = false, dedupe = false } = opts

  const key = `${name}.${action}.${JSON.stringify(payload)}`
  if (dedupe && inflight.has(key)) return inflight.get(key)

  if (loading) wx.showLoading({ title: loading, mask: true })

  const run = () =>
    wx.cloud.callFunction({
      name,
      data: { action, payload },
    })

  const promise = run()
    .then((res) => {
      const body = res && res.result ? res.result : {}
      if (body.ok === false) {
        const err = new Error(body.message || '请求失败')
        err.business = true
        err.code = body.code || ''
        throw err
      }
      return body.data
    })
    .catch(async (err) => {
      // 业务性失败不重试；网络类失败重试一次
      if (!noRetry && err && !err.business) {
        try {
          const retry = await run()
          const body = retry && retry.result ? retry.result : {}
          if (body.ok === false) throw new Error(body.message || '请求失败')
          return body.data
        } catch (e) {
          /* fallthrough */
        }
      }
      throw err
    })
    .finally(() => {
      if (loading) wx.hideLoading()
      inflight.delete(key)
    })

  if (dedupe) inflight.set(key, promise)

  return promise.catch((err) => {
    if (!silent) toast(err.message)
    throw err
  })
}

module.exports = { call }
