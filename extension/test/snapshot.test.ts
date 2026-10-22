import { describe, it, expect, beforeAll } from 'vitest'
import { buildSnapshot, type Entry } from '../src/content/snapshot'

// happy-dom has no layout, so give every element a non-zero box; visibility then rests on CSS, as in Chrome.
beforeAll(() => {
  Element.prototype.getBoundingClientRect = () => ({ width: 10, height: 10, top: 0, left: 0, right: 10, bottom: 10, x: 0, y: 0, toJSON() {} }) as DOMRect
})

const snap = (html: string) => { document.body.innerHTML = html; const map = new Map<number, Entry>(); return { s: buildSnapshot(document, map, 1), map } }

describe('snapshot', () => {
  it('numbers interactive elements and reads their names', () => {
    const { s, map } = snap('<button>Go</button><a href="/x">Link</a>')
    expect(s.lines[0]).toMatch(/^\[1\] button "Go"/)
    expect(s.lines[1]).toMatch(/^\[2\] link "Link"/)
    expect(map.get(1)!.name).toBe('Go')
  })
  it('redacts password values', () => {
    const j = snap('<input type="password" value="hunter2">').s.lines.join('\n')
    expect(j).toContain('value="<redacted>"')
    expect(j).not.toContain('hunter2')
  })
  it('skips display:none elements', () => {
    const j = snap('<button style="display:none">Hidden</button><button>Shown</button>').s.lines.join('\n')
    expect(j).not.toContain('Hidden')
    expect(j).toContain('Shown')
  })
  it('prefers aria-label for the name', () => {
    expect(snap('<button aria-label="Close dialog">x</button>').s.lines[0]).toContain('"Close dialog"')
  })
  it('walks open shadow DOM', () => {
    document.body.innerHTML = '<div id="host"></div>'
    document.getElementById('host')!.attachShadow({ mode: 'open' }).innerHTML = '<button>Inside</button>'
    const map = new Map<number, Entry>()
    expect(buildSnapshot(document, map, 1).lines.join('\n')).toContain('"Inside"')
  })
})
