// Tiny DOM helpers (spec section 8: plain TypeScript and DOM, no framework).
export function h(tag: string, props: any = {}, ...kids: any[]): HTMLElement {
  const e = document.createElement(tag)
  Object.assign(e, props)
  for (const k of kids.flat()) { if (k == null) continue; e.append(k.nodeType ? k : document.createTextNode(String(k))) }
  return e
}

export function renderTable(columns: string[], rows: string[][]): HTMLElement {
  const t = document.createElement('table')
  const head = document.createElement('tr')
  for (const c of columns) { const th = document.createElement('th'); th.textContent = c; head.append(th) }
  t.append(head)
  for (const r of rows) {
    const tr = document.createElement('tr')
    for (const c of r) { const td = document.createElement('td'); td.textContent = c; tr.append(td) }
    t.append(tr)
  }
  return t
}
