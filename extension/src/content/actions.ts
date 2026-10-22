// Action executors (spec section 5) plus the stale check (section 4). Each returns {success, method, details}.
import type { Entry } from './snapshot'

export type Result = { success: boolean; method: string; details: string }
export type Req = {
  v: number; n?: number; tool: string
  text?: string; clear?: boolean; submit?: boolean; mode?: string
  value?: string; key?: string; direction?: string; amount?: string; timeout_ms?: number
}

const nameOf = (el: Element): string => (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80)

// Spec section 4: before any action, reject if the snapshot moved on, the element is gone, or it changed.
function resolve(req: Req, map: Map<number, Entry>, v: number): Element | Result {
  if (req.v !== v) return { success: false, method: 'none', details: 'stale' }
  const entry = req.n != null ? map.get(req.n) : undefined
  if (req.n != null && !entry) return { success: false, method: 'none', details: 'stale' }
  if (!entry) return { success: false, method: 'none', details: 'no element' }
  const el = entry.ref.deref()
  if (!el || !el.isConnected) return { success: false, method: 'none', details: 'stale' }
  if (el.getAttribute('role') && el.getAttribute('role') !== entry.role) return { success: false, method: 'none', details: 'stale' }
  if (nameOf(el) && entry.name && nameOf(el) !== entry.name) return { success: false, method: 'none', details: 'stale' }
  return el
}

const setValue = (el: HTMLElement, text: string) => {
  if ((el as HTMLElement).isContentEditable) { el.focus(); document.execCommand('insertText', false, text); return }
  const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype
  const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set
  el.focus()
  setter?.call(el, text)
  el.dispatchEvent(new Event('input', { bubbles: true }))
  el.dispatchEvent(new Event('change', { bubbles: true }))
}

export async function runAction(req: Req, map: Map<number, Entry>, v: number): Promise<Result> {
  // click/type/select always need their element; scroll/press_key check an id if one was given;
  // wait_for never resolves (it polls by text or by id presence).
  const needsEl = req.tool === 'click' || req.tool === 'type' || req.tool === 'select_option'
  const doResolve = needsEl || (req.n != null && req.tool !== 'wait_for')
  const got = doResolve ? resolve(req, map, v) : null
  if (got && 'success' in got) return got
  const el = (got && !('success' in got) ? got : null) as HTMLElement | null

  try {
    switch (req.tool) {
      case 'click': {
        if (!el) return { success: false, method: 'none', details: 'no element' }
        el.scrollIntoView({ block: 'center' })
        if (req.mode === 'hover') { el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })); el.dispatchEvent(new MouseEvent('mouseenter', { bubbles: true })); return { success: true, method: 'hover', details: '' } }
        if (req.mode === 'right') { el.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true })); return { success: true, method: 'contextmenu', details: '' } }
        if (req.mode === 'double') { el.dispatchEvent(new MouseEvent('dblclick', { bubbles: true })); return { success: true, method: 'dblclick', details: '' } }
        el.click()
        return { success: true, method: 'click', details: '' }
      }
      case 'type': {
        if (!el) return { success: false, method: 'none', details: 'no element' }
        if (req.clear) setValue(el, '')
        setValue(el, req.text || '')
        if (req.submit) {
          const form = (el as HTMLInputElement).form
          if (form) form.requestSubmit()
          else el.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
        }
        return { success: true, method: 'type', details: '' }
      }
      case 'select_option': {
        const sel = el as HTMLSelectElement | null
        if (!sel) return { success: false, method: 'none', details: 'no element' }
        const want = req.value || ''
        const opt = Array.from(sel.options).find(o => o.value === want || o.label === want || o.textContent?.trim() === want)
        if (!opt) return { success: false, method: 'none', details: 'option not found' }
        sel.value = opt.value
        sel.dispatchEvent(new Event('change', { bubbles: true }))
        return { success: true, method: 'select', details: opt.value }
      }
      case 'press_key': {
        const target: EventTarget = el || document.activeElement || document.body
        target.dispatchEvent(new KeyboardEvent('keydown', { key: req.key, bubbles: true }))
        target.dispatchEvent(new KeyboardEvent('keyup', { key: req.key, bubbles: true }))
        return { success: true, method: 'key', details: req.key || '' }
      }
      case 'scroll': {
        const box = (el as Element) || document.scrollingElement || document.body
        const by = req.amount === 'end' ? 1e6 : (box.clientHeight || innerHeight)
        box.scrollBy({ top: req.direction === 'up' ? -by : by })
        return { success: true, method: 'scroll', details: req.direction || 'down' }
      }
      case 'wait_for': {
        const deadline = Date.now() + Math.min(req.timeout_ms || 5000, 10000)
        while (Date.now() < deadline) {
          if (req.text && document.body.innerText.includes(req.text)) return { success: true, method: 'wait', details: 'text found' }
          if (req.n != null && map.get(req.n)?.ref.deref()?.isConnected) return { success: true, method: 'wait', details: 'element present' }
          await new Promise(r => setTimeout(r, 200))
        }
        return { success: false, method: 'none', details: 'timeout' }
      }
      default:
        return { success: false, method: 'none', details: `unknown tool ${req.tool}` }
    }
  } catch (e) {
    return { success: false, method: 'none', details: String((e as Error).message || e) }
  }
}
