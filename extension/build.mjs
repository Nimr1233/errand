// Bundle to dist/: the content script as a classic IIFE (it is injected into every frame with
// chrome.scripting), the service worker and panel as ES modules. Then copy the manifest and panel HTML.
import { build } from 'esbuild'
import { copyFileSync, mkdirSync } from 'node:fs'

mkdirSync('dist', { recursive: true })
const common = { bundle: true, target: 'chrome120', logLevel: 'info' }

await build({ ...common, entryPoints: { content: 'src/content/index.ts' }, outdir: 'dist', format: 'iife' })
await build({ ...common, entryPoints: { sw: 'src/sw.ts', panel: 'src/panel/main.ts' }, outdir: 'dist', format: 'esm' })

copyFileSync('manifest.json', 'dist/manifest.json')
copyFileSync('src/panel/index.html', 'dist/index.html')
console.log('Built dist/. Load it in Chrome: chrome://extensions -> Developer mode -> Load unpacked -> dist')
