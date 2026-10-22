import { defineConfig } from '@playwright/test'

// e2e needs the Chromium that Playwright downloads: npm run build, then npx playwright install chromium, then npm run e2e.
export default defineConfig({ testDir: 'e2e', use: { headless: true } })
