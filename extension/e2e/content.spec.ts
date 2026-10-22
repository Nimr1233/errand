import { test, expect } from '@playwright/test'
import { pathToFileURL } from 'node:url'

// Exercises the built content script in real Chromium: snapshot sees the list, a click reorders it, and
// the old id then reads as stale. Requires `npm run build` first (it loads dist/content.js).
test('content script: snapshot, click, stale id', async ({ page }) => {
  await page.goto(pathToFileURL('test/fixtures/spa-reorder.html').href)
  await page.addScriptTag({ path: 'dist/content.js' })

  const snap: any = await page.evaluate(() => (window as any).__errand.snapshot(1))
  expect(snap.lines.join('\n')).toContain('Blue mug')
  const blueAdd = snap.lines.findIndex((l: string) => l.includes('button')) // first Add button id n=1

  const ok: any = await page.evaluate((n) => (window as any).__errand.act({ v: 1, n, tool: 'click' }), blueAdd + 1)
  expect(ok.success).toBe(true)

  // Snapshot moved on (v=1 still): acting on the pre-click map against a new version is rejected.
  const stale: any = await page.evaluate(() => (window as any).__errand.act({ v: 2, n: 1, tool: 'click' }))
  expect(stale.details).toBe('stale')
})
