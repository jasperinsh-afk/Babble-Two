(() => {
  'use strict'
  const config = window.CONTENT_CONFIG
  const $ = (selector) => document.querySelector(selector)
  const state = { view: config.initialView || 'layout', layout: null, items: [], schema: null, defaults: {}, editingId: '', dirty: false, draggedId: '' }
  const clone = (value) => JSON.parse(JSON.stringify(value))
  const sectionName = (type) => Object.fromEntries(config.sectionTypes)[type] || type

  function notice(message, error = false) {
    const el = $('#cms-notice')
    el.textContent = message
    el.className = `cms-notice is-visible${error ? ' is-error' : ''}`
    clearTimeout(notice.timer)
    notice.timer = setTimeout(() => { el.className = 'cms-notice' }, 4200)
  }

  function markDirty() {
    state.dirty = true
    $('#cms-save').classList.add('has-changes')
    $('#cms-save').textContent = '保存更改'
  }

  async function request(path, options = {}) {
    const response = await fetch(`/admin/web/content/api${path}`, {
      credentials: 'same-origin',
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    })
    if (response.redirected && response.url.includes('/login')) {
      window.location.href = '/admin/web/login'
      throw new Error('登录已过期')
    }
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body.detail || body.message || '操作失败，请重试')
    return body.data
  }

  function button(text, className, onClick) {
    const el = document.createElement('button')
    el.type = 'button'
    el.textContent = text
    if (className) el.className = className
    el.addEventListener('click', onClick)
    return el
  }

  function fieldControl(field, value, onChange) {
    const wrap = document.createElement('div')
    wrap.className = `cms-field cms-field--${field.type}`
    const label = document.createElement('label')
    label.textContent = field.label + (field.required ? ' *' : '')
    wrap.append(label)
    if (field.type === 'stringList') {
      const input = document.createElement('textarea')
      input.rows = 4
      input.value = Array.isArray(value) ? value.join('\n') : ''
      input.addEventListener('input', () => onChange(input.value.split('\n').map((item) => item.trim()).filter(Boolean)))
      wrap.append(input)
      return wrap
    }
    if (field.type === 'list') {
      const list = document.createElement('div')
      list.className = 'cms-nested-list'
      const rows = Array.isArray(value) ? value : []
      const renderRows = () => {
        list.replaceChildren()
        rows.forEach((item, index) => {
          const row = document.createElement('div')
          row.className = 'cms-nested-item'
          const head = document.createElement('div')
          head.className = 'cms-nested-item__head'
          const title = document.createElement('strong')
          title.textContent = `${field.itemLabel || '项目'} ${index + 1}`
          const actions = document.createElement('div')
          actions.className = 'cms-row-actions'
          const move = (delta) => {
            const target = index + delta
            if (target < 0 || target >= rows.length) return
            ;[rows[index], rows[target]] = [rows[target], rows[index]]
            onChange(rows)
            renderRows()
          }
          actions.append(
            button('↑', 'ghost', () => move(-1)),
            button('↓', 'ghost', () => move(1)),
            button('删除', 'ghost cms-danger-text', () => { rows.splice(index, 1); onChange(rows); renderRows() }),
          )
          head.append(title, actions)
          const grid = document.createElement('div')
          grid.className = 'cms-fields cms-fields--nested'
          field.fields.forEach((subfield) => grid.append(fieldControl(subfield, item[subfield.name], (next) => { item[subfield.name] = next; onChange(rows) })))
          row.append(head, grid)
          list.append(row)
        })
        list.append(button(`添加${field.itemLabel || '项目'}`, 'ghost cms-add-row', () => {
          const item = {}
          field.fields.forEach((subfield) => { item[subfield.name] = subfield.type === 'number' ? rows.length : '' })
          rows.push(item)
          onChange(rows)
          renderRows()
        }))
      }
      renderRows()
      wrap.append(list)
      return wrap
    }
    let input
    if (field.type === 'textarea') {
      input = document.createElement('textarea')
      input.rows = 4
      input.value = value || ''
    } else if (field.type === 'select') {
      input = document.createElement('select')
      input.append(new Option('请选择', ''))
      field.options.forEach(([optionValue, optionLabel]) => input.append(new Option(optionLabel, optionValue)))
      input.value = value || ''
    } else if (field.type === 'boolean') {
      input = document.createElement('input')
      input.type = 'checkbox'
      input.checked = Boolean(value)
      wrap.classList.add('cms-field--check')
    } else {
      input = document.createElement('input')
      input.type = field.type === 'datetime' ? 'datetime-local' : field.type === 'number' ? 'number' : 'text'
      if (field.type === 'url') input.inputMode = 'url'
      input.value = field.type === 'datetime' && value ? String(value).slice(0, 16) : (value ?? '')
      if (field.type === 'number') input.step = 'any'
      if (field.placeholder) input.placeholder = field.placeholder
    }
    input.required = Boolean(field.required)
    input.addEventListener('input', () => onChange(field.type === 'boolean' ? input.checked : field.type === 'number' && input.value !== '' ? Number(input.value) : input.value))
    input.addEventListener('change', () => onChange(field.type === 'boolean' ? input.checked : field.type === 'number' && input.value !== '' ? Number(input.value) : input.value))
    wrap.append(input)
    return wrap
  }

  function sectionFields(section) {
    const container = document.createElement('div')
    container.className = 'cms-fields cms-fields--section'
    container.append(fieldControl({ name: 'type', label: '版块类型', type: 'select', options: config.sectionTypes, required: true }, section.type, (value) => {
      section.type = value
      section.title = sectionName(value)
      markDirty()
      renderSections()
    }))
    container.append(fieldControl({ name: 'title', label: '用户端标题', type: 'text', required: true }, section.title, (value) => { section.title = value; markDirty() }))
    if (section.type !== 'todayPoll' && section.type !== 'quickEntries') {
      container.append(fieldControl({ name: 'limit', label: '最多显示条数', type: 'number', required: true }, section.config.limit || 5, (value) => { section.config.limit = value; markDirty() }))
    }
    if (section.type === 'quickEntries') {
      container.append(fieldControl({ name: 'items', label: '快捷入口', type: 'list', itemLabel: '入口', fields: [
        { name: 'label', label: '名称', type: 'text', required: true },
        { name: 'icon', label: '图标字符', type: 'text' },
        { name: 'to', label: '站内路径', type: 'text', required: true, placeholder: '/vote' },
        { name: 'key', label: '样式标识', type: 'text' },
      ] }, section.config.items || [], (value) => { section.config.items = value; markDirty() }))
    }
    return container
  }

  function renderSections() {
    const list = $('#cms-sections')
    list.replaceChildren()
    state.layout.sections.forEach((section, index) => {
      const node = $('#cms-section-template').content.firstElementChild.cloneNode(true)
      node.dataset.id = section.id
      node.querySelector('.cms-section__number').textContent = String(index + 1).padStart(2, '0')
      node.querySelector('.cms-section__heading strong').textContent = section.title || sectionName(section.type)
      node.querySelector('.cms-section__heading small').textContent = sectionName(section.type)
      const enabled = node.querySelector('.cms-switch input')
      enabled.checked = section.enabled !== false
      enabled.addEventListener('change', () => { section.enabled = enabled.checked; node.classList.toggle('is-disabled', !enabled.checked); markDirty() })
      node.classList.toggle('is-disabled', !enabled.checked)
      const move = (delta) => {
        const target = index + delta
        if (target < 0 || target >= state.layout.sections.length) return
        ;[state.layout.sections[index], state.layout.sections[target]] = [state.layout.sections[target], state.layout.sections[index]]
        markDirty()
        renderSections()
      }
      node.querySelector('.cms-up').disabled = index === 0
      node.querySelector('.cms-down').disabled = index === state.layout.sections.length - 1
      node.querySelector('.cms-up').addEventListener('click', () => move(-1))
      node.querySelector('.cms-down').addEventListener('click', () => move(1))
      node.querySelector('.cms-remove-section').addEventListener('click', () => {
        if (!window.confirm(`确定删除“${section.title}”版块吗？保存后生效。`)) return
        state.layout.sections.splice(index, 1)
        markDirty()
        renderSections()
      })
      const fields = node.querySelector('.cms-section__fields')
      fields.append(sectionFields(section))
      node.querySelector('.cms-expand').addEventListener('click', (event) => {
        fields.classList.toggle('hidden')
        event.currentTarget.textContent = fields.classList.contains('hidden') ? '编辑字段' : '收起字段'
      })
      node.addEventListener('dragstart', () => { state.draggedId = section.id; node.classList.add('is-dragging') })
      node.addEventListener('dragend', () => { state.draggedId = ''; node.classList.remove('is-dragging') })
      node.addEventListener('dragover', (event) => event.preventDefault())
      node.addEventListener('drop', (event) => {
        event.preventDefault()
        const from = state.layout.sections.findIndex((item) => item.id === state.draggedId)
        if (from < 0 || from === index) return
        const [dragged] = state.layout.sections.splice(from, 1)
        state.layout.sections.splice(index, 0, dragged)
        markDirty()
        renderSections()
      })
      list.append(node)
    })
    $('#cms-empty').classList.add('hidden')
    if (!state.layout.sections.length) {
      const empty = document.createElement('div')
      empty.className = 'cms-empty'
      empty.textContent = '首页暂无版块，点击“添加版块”开始搭建。'
      list.append(empty)
    }
  }

  async function loadLayout() {
    $('#cms-sections').innerHTML = '<div class="cms-loading">正在读取首页配置…</div>'
    try {
      state.layout = await request('/layout')
      state.layout.sections.forEach((section) => { section.config ||= {} })
      renderSections()
    } catch (error) {
      $('#cms-sections').innerHTML = `<div class="cms-empty">读取失败：${error.message}</div>`
    }
  }

  function renderDocuments() {
    const list = $('#cms-list')
    list.replaceChildren()
    $('#cms-count').textContent = `${state.items.length} 条内容`
    $('#cms-empty').classList.toggle('hidden', state.items.length > 0)
    const titleKey = state.schema.titleKey
    state.items.forEach((item) => {
      const row = document.createElement('article')
      row.className = 'cms-document'
      const info = document.createElement('div')
      info.className = 'cms-document__info'
      const title = document.createElement('strong')
      title.textContent = item[titleKey] || '（未命名）'
      const meta = document.createElement('span')
      meta.textContent = [item.status, item.category || item.tag, `ID: ${item._id}`].filter(Boolean).join(' · ')
      info.append(title, meta)
      const actions = document.createElement('div')
      actions.className = 'cms-row-actions'
      actions.append(button('编辑', 'ghost', () => openEditor(item)))
      actions.append(button('删除', 'ghost cms-danger-text', async () => {
        if (!window.confirm(`确定永久删除“${item[titleKey] || item._id}”吗？此操作不可撤销。`)) return
        try {
          await request(`/${state.view}/${encodeURIComponent(item._id)}`, { method: 'DELETE' })
          state.items = state.items.filter((entry) => entry._id !== item._id)
          renderDocuments()
          notice('内容已删除')
        } catch (error) { notice(error.message, true) }
      }))
      row.append(info, actions)
      list.append(row)
    })
  }

  async function loadCollection() {
    $('#cms-loading').classList.remove('hidden')
    $('#cms-list').replaceChildren()
    $('#cms-empty').classList.add('hidden')
    $('#cms-collection-title').textContent = config.schemas[state.view].label
    try {
      const data = await request(`/${state.view}`)
      state.items = data.items
      state.schema = data.schema
      state.defaults = data.defaults
      renderDocuments()
    } catch (error) {
      $('#cms-list').innerHTML = `<div class="cms-empty">读取失败：${error.message}</div>`
    } finally {
      $('#cms-loading').classList.add('hidden')
    }
  }

  function openEditor(item) {
    state.editingId = item._id || ''
    const draft = clone(item)
    $('#cms-editor-title').textContent = `${state.editingId ? '编辑' : '新增'}${state.schema.label}`
    const fields = $('#cms-fields')
    fields.replaceChildren()
    state.schema.fields.forEach((field) => fields.append(fieldControl(field, draft[field.name], (value) => { draft[field.name] = value })))
    const form = $('#cms-form')
    form.onsubmit = async (event) => {
      event.preventDefault()
      if (!form.reportValidity()) return
      const submit = $('#cms-submit')
      submit.disabled = true
      submit.textContent = '保存中…'
      try {
        const path = state.editingId ? `/${state.view}/${encodeURIComponent(state.editingId)}` : `/${state.view}`
        await request(path, { method: state.editingId ? 'PUT' : 'POST', body: JSON.stringify(draft) })
        $('#cms-editor').close()
        await loadCollection()
        notice('保存成功，用户端已同步')
      } catch (error) { notice(error.message, true) } finally {
        submit.disabled = false
        submit.textContent = '保存内容'
      }
    }
    $('#cms-editor').showModal()
  }

  async function switchView(view) {
    if (state.dirty && !window.confirm('首页还有未保存的修改，确定离开吗？')) return
    state.view = view
    state.dirty = false
    $('#cms-save').classList.remove('has-changes')
    document.querySelectorAll('.cms-tab').forEach((tab) => {
      const active = tab.dataset.view === view
      tab.classList.toggle('is-active', active)
      tab.setAttribute('aria-selected', String(active))
    })
    const isLayout = view === 'layout'
    $('#cms-layout').classList.toggle('hidden', !isLayout)
    $('#cms-documents').classList.toggle('hidden', isLayout)
    $('#cms-save').classList.toggle('hidden', !isLayout)
    $('#cms-add').classList.toggle('hidden', isLayout || !config.canCreate || config.schemas[view]?.canCreate === false)
    $('#cms-save').textContent = '保存首页'
    if (isLayout) await loadLayout()
    else await loadCollection()
  }

  document.querySelectorAll('.cms-tab').forEach((tab) => tab.addEventListener('click', () => switchView(tab.dataset.view)))
  $('#cms-add').addEventListener('click', () => openEditor(clone(state.defaults)))
  $('#cms-add-section').addEventListener('click', () => {
    state.layout.sections.push({ id: `section-${Date.now()}`, type: 'banner', title: 'Banner 轮播', enabled: true, config: { limit: 5 } })
    markDirty()
    renderSections()
    $('#cms-sections').lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
  $('#cms-save').addEventListener('click', async () => {
    const save = $('#cms-save')
    save.disabled = true
    save.textContent = '保存中…'
    try {
      state.layout = await request('/layout', { method: 'PUT', body: JSON.stringify(state.layout) })
      state.dirty = false
      save.classList.remove('has-changes')
      renderSections()
      notice('首页已保存，用户端已同步')
    } catch (error) { notice(error.message, true) } finally {
      save.disabled = false
      save.textContent = state.dirty ? '保存更改' : '保存首页'
    }
  })
  $('#cms-close').addEventListener('click', () => $('#cms-editor').close())
  $('#cms-cancel').addEventListener('click', () => $('#cms-editor').close())
  $('#cms-editor').addEventListener('click', (event) => { if (event.target === $('#cms-editor')) $('#cms-editor').close() })
  window.addEventListener('beforeunload', (event) => { if (state.dirty) { event.preventDefault(); event.returnValue = '' } })
  switchView(state.view)
})()
