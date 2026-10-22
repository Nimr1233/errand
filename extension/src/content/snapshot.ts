// Snapshot builder (spec section 4): turn one frame's DOM into a short text list of the things an agent
// can act on, plus headings and short text for context. Runs in the page; the panel merges frames and
// adds the [page]/[tabs] header and the f{frameId}: prefix.
export type Entry = { ref: WeakRef<Element>; role: string; name: string }
export type Snap = { lines: string[]; cut: number; version: number }

const LIMIT = 60000
const ROLE_WIDGETS = new Set(['button', 'link', 'checkbox', 'radio', 'tab', 'menuitem', 'option', 'switch',
  'combobox', 'textbox', 'slider'])
const REDACT = /card|cc-?num|cvc|cvv|otp|one.?time|security.?code/i

const vis = (el: Element): boolean => {
  const s = getComputedStyle(el)
  if (s.display === 'none' || s.visibility === 'hidden' || s.opacity === '0') return false
  const r = el.getBoundingClientRect()
  return r.width > 0 && r.height > 0
}

const onscreen = (el: Element): boolean => {
  const r = el.getBoundingClientRect()
  return r.bottom > 0 && r.right > 0 && r.top < innerHeight && r.left < innerWidth
}

const text = (el: Element): string => (el.textContent || '').replace(/\s+/g, ' ').trim()
const esc = (s: string): string => (typeof CSS !== 'undefined' && CSS.escape) ? CSS.escape(s) : s.replace(/["\\]/g, '\\$&')

const role = (el: Element): string => {
  const explicit = el.getAttribute('role')
  if (explicit) return explicit
  const tag = el.tagName.toLowerCase()
  if (tag === 'a' && el.hasAttribute('href')) return 'link'
  if (tag === 'button') return 'button'
  if (tag === 'select') return 'combobox'
  if (tag === 'textarea') return 'textbox'
  if (tag.match(/^h[1-6]$/)) return 'heading'
  if (tag === 'input') {
    const t = (el.getAttribute('type') || 'text').toLowerCase()
    if (t === 'checkbox') return 'checkbox'
    if (t === 'radio') return 'radio'
    if (['button', 'submit', 'reset', 'image'].includes(t)) return 'button'
    return 'textbox'
  }
  if ((el as HTMLElement).isContentEditable) return 'textbox'
  return ''
}

const clickable = (el: Element): boolean => {
  if (getComputedStyle(el).cursor !== 'pointer') return false
  return !!(el as HTMLElement).onclick || el.hasAttribute('onclick') || el.hasAttribute('tabindex')
}

const name = (el: Element): string => {
  const by = el.getAttribute('aria-labelledby')
  if (by) {
    const t = by.split(/\s+/).map(id => el.ownerDocument.getElementById(id)?.textContent || '').join(' ').trim()
    if (t) return t.slice(0, 80)
  }
  const aria = el.getAttribute('aria-label')
  if (aria) return aria.trim().slice(0, 80)
  const id = el.id
  if (id) {
    const lbl = el.ownerDocument.querySelector(`label[for="${esc(id)}"]`)
    if (lbl) return text(lbl).slice(0, 80)
  }
  const wrap = el.closest('label')
  if (wrap) return text(wrap).slice(0, 80)
  for (const a of ['alt', 'title', 'placeholder']) {
    const v = el.getAttribute(a)
    if (v) return v.trim().slice(0, 80)
  }
  return text(el).slice(0, 80)
}

const value = (el: Element): string | null => {
  const tag = el.tagName.toLowerCase()
  if (tag !== 'input' && tag !== 'textarea' && tag !== 'select') return null
  const t = (el.getAttribute('type') || '').toLowerCase()
  const auto = el.getAttribute('autocomplete') || ''
  if (t === 'password' || auto === 'one-time-code' || auto === 'cc-number' || REDACT.test(el.id + ' ' + (el.getAttribute('name') || '')))
    return '<redacted>'
  return (el as HTMLInputElement).value || ''
}

const state = (el: Element): string => {
  const bits: string[] = []
  const a = (n: string) => el.getAttribute(n)
  if ((el as HTMLInputElement).disabled || a('aria-disabled') === 'true') bits.push('disabled')
  if ((el as HTMLInputElement).checked || a('aria-checked') === 'true') bits.push('checked')
  if (a('aria-expanded')) bits.push(a('aria-expanded') === 'true' ? 'expanded' : 'collapsed')
  if ((el as HTMLOptionElement).selected || a('aria-selected') === 'true') bits.push('selected')
  return bits.length ? ' ' + bits.join(' ') : ''
}

// Walk the tree (into open shadow roots), collecting what we keep in document order.
function collect(root: ParentNode, out: Element[]) {
  for (const el of Array.from(root.children)) {
    const tag = el.tagName.toLowerCase()
    if (tag === 'script' || tag === 'style' || el.getAttribute('aria-hidden') === 'true') continue
    if (!vis(el)) continue
    const r = role(el)
    if (ROLE_WIDGETS.has(r) || r === 'heading' || (el as HTMLElement).isContentEditable || clickable(el)) out.push(el)
    else if (!r && text(el) && text(el).length <= 200 && !el.children.length) out.push(el) // short text block
    if ((el as HTMLElement).shadowRoot) collect((el as HTMLElement).shadowRoot!, out)
    collect(el, out)
  }
}

export function buildSnapshot(doc: Document, map: Map<number, Entry>, v: number): Snap {
  map.clear()
  const found: Element[] = []
  collect(doc.body || doc.documentElement, found)
  found.sort((a, b) => Number(onscreen(b)) - Number(onscreen(a))) // on-screen first, stable keeps doc order within
  let n = 0, used = 0, cut = 0
  const el: string[] = [], txt: string[] = []
  for (const e of found) {
    const r = role(e)
    let line: string
    if (ROLE_WIDGETS.has(r) || (e as HTMLElement).isContentEditable || clickable(e)) {
      n++
      map.set(n, { ref: new WeakRef(e), role: r || 'button', name: name(e) })
      const val = value(e)
      line = `[${n}] ${r || 'button'} "${name(e)}"${state(e)}${val !== null ? ` value="${val}"` : ''}`
    } else {
      line = r === 'heading' ? `heading: "${name(e)}"` : `text: "${text(e)}"`
    }
    if (used + line.length > LIMIT) { cut++; continue }
    used += line.length + 1
    ;(line.startsWith('[') ? el : txt).push(line)
  }
  return { lines: [...el, ...txt], cut, version: v }
}
