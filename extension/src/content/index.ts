// Injected into every frame on demand (spec section 3). Exposes window.__errand in the isolated world,
// holding this frame's element map. A guard makes re-injection safe.
import { buildSnapshot, type Entry } from './snapshot'
import { runAction, type Req } from './actions'

declare global {
  interface Window { __errand?: { snapshot: (v: number) => unknown; act: (req: Req) => Promise<unknown> } }
}

if (!window.__errand) {
  const map = new Map<number, Entry>()
  let version = 0
  window.__errand = {
    snapshot(v: number) { version = v; return buildSnapshot(document, map, v) },
    act(req: Req) { return runAction(req, map, version) },
  }
}
