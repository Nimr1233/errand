// Side panel controller (spec section 8): screens, the Run/Stop buttons, the confirm card and ask box,
// results with CSV/Copy, history, settings, and the resume banner.
import { h, renderTable } from './ui'
import { getSettings, setSettings, saveRun, listRuns, getRun, type Run, type Settings } from './store'
import { runTask } from './loop'
import { toCSV, toTSV } from './csv'

const $ = (id: string) => document.getElementById(id)!
let controller: AbortController | null = null
let current: Run | null = null
let pending: ((v: any) => void) | null = null  // resolves the confirm or ask promise the loop is awaiting

function showScreen(name: string) {
  for (const s of ['run', 'results', 'history', 'settings']) ($(s) as HTMLElement).hidden = s !== name
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('on', (b as HTMLElement).dataset.screen === name))
}
document.querySelectorAll('nav button').forEach(b => b.addEventListener('click', () => showScreen((b as HTMLElement).dataset.screen!)))

const currentTab = async () => (await chrome.tabs.query({ active: true, currentWindow: true }))[0]

const hooks = {
  confirm: (c: { text: string }) => new Promise<boolean>(res => { pending = res; const card = $('confirm'); card.hidden = false; card.querySelector('.what')!.textContent = c.text }),
  ask: (q: string) => new Promise<string>(res => { pending = res; const box = $('ask'); box.hidden = false; box.querySelector('.q')!.textContent = q }),
}
$('confirm-yes').addEventListener('click', () => { $('confirm').hidden = true; pending?.(true); pending = null })
$('confirm-no').addEventListener('click', () => { $('confirm').hidden = true; pending?.(false); pending = null })
$('ask-send').addEventListener('click', () => { $('ask').hidden = true; pending?.(($('ask-input') as HTMLInputElement).value); pending = null })

function onEvent(e: any) {
  if (e.type === 'step') $('feed').prepend(h('div', { className: 'step' }, `${e.name} ${e.result?.success ? '✓' : '✗'} ${e.input?.id || ''} ${e.result?.details || ''}`))
  else if (e.type === 'rows') renderResults(e.columns, e.rows)
  else if (e.type === 'answer') $('answer').textContent = 'Answer: ' + e.text
  else if (e.type === 'retry') $('status').textContent = 'Paused (server busy). Press Run to retry.'
  else if (e.type === 'end') { ($('run-btn') as HTMLElement).hidden = false; ($('stop-btn') as HTMLElement).hidden = true; $('status').textContent = 'Status: ' + e.status; refreshHistory() }
}

async function start(task: string, run?: Run) {
  if (!await chrome.permissions.request({ origins: ['<all_urls>'] })) { $('status').textContent = 'Errand needs permission to read pages.'; return }
  const settings = await getSettings()
  const tab = await currentTab()
  current = run || { id: String(Date.now()), task, status: 'running', tabId: tab.id!, step: 0, messages: [], rows: [], columns: [], createdAt: Date.now() }
  await saveRun(current)
  controller = new AbortController()
  ;($('run-btn') as HTMLElement).hidden = true; ($('stop-btn') as HTMLElement).hidden = false
  $('feed').textContent = ''; $('answer').textContent = ''; $('status').textContent = 'Running…'
  try { await runTask(current, settings, onEvent, hooks, controller.signal) }
  catch (e: any) { $('status').textContent = 'Error: ' + String(e.message || e); ($('run-btn') as HTMLElement).hidden = false; ($('stop-btn') as HTMLElement).hidden = true }
}
$('run-btn').addEventListener('click', () => { const t = ($('task') as HTMLTextAreaElement).value.trim(); if (t) start(t) })
$('stop-btn').addEventListener('click', () => controller?.abort())

function renderResults(columns: string[], rows: string[][]) { const box = $('table'); box.textContent = ''; box.append(renderTable(columns, rows)) }
$('csv').addEventListener('click', () => {
  if (!current) return
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([toCSV(current.columns, current.rows)], { type: 'text/csv' }))
  a.download = 'errand.csv'; a.click()
})
$('copy').addEventListener('click', () => { if (current) navigator.clipboard.writeText(toTSV(current.columns, current.rows)) })

async function refreshHistory() {
  const box = $('history'); box.textContent = ''
  for (const r of await listRuns())
    box.append(h('div', {}, h('button', { onclick: () => openRun(r.id) }, `${r.task.slice(0, 40)} — ${r.status} (${r.rows.length} rows)`)))
}
async function openRun(id: string) { const r = await getRun(id); if (r) { current = r; renderResults(r.columns, r.rows); showScreen('results') } }

async function loadSettings() {
  const s = await getSettings()
  ;($('set-baseUrl') as HTMLInputElement).value = s.baseUrl
  ;($('set-key') as HTMLInputElement).value = s.key
  ;($('set-model') as HTMLInputElement).value = s.model
  ;($('set-maxSteps') as HTMLInputElement).value = String(s.maxSteps)
  ;($('set-confirm') as HTMLInputElement).checked = s.confirm
}
$('set-save').addEventListener('click', async () => {
  const s: Settings = {
    baseUrl: ($('set-baseUrl') as HTMLInputElement).value, key: ($('set-key') as HTMLInputElement).value,
    model: ($('set-model') as HTMLInputElement).value, maxSteps: Number(($('set-maxSteps') as HTMLInputElement).value) || 40,
    confirm: ($('set-confirm') as HTMLInputElement).checked,
  }
  await setSettings(s); $('set-status').textContent = 'Saved.'
})
$('set-test').addEventListener('click', async () => {
  try { const r = await fetch(($('set-baseUrl') as HTMLInputElement).value.replace(/\/$/, '') + '/models'); $('set-status').textContent = r.ok ? 'Server reachable.' : 'Server said ' + r.status }
  catch (e: any) { $('set-status').textContent = 'No server: ' + String(e.message) }
})

async function checkResume() {
  const r = (await listRuns()).find(x => ['running', 'waiting_for_user', 'paused', 'confirming'].includes(x.status))
  if (!r) return
  ;($('resume') as HTMLElement).hidden = false
  $('resume-btn').addEventListener('click', () => { ($('resume') as HTMLElement).hidden = true; start(r.task, r) })
  $('resume-skip').addEventListener('click', () => { ($('resume') as HTMLElement).hidden = true })
}

loadSettings(); refreshHistory(); checkResume()
