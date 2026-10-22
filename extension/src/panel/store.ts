// Runs, the run index and settings in chrome.storage.local (spec section 8).
export type Settings = { baseUrl: string; key: string; model: string; maxSteps: number; confirm: boolean }
export type Run = { id: string; task: string; status: string; tabId: number; step: number; messages: any[]; rows: string[][]; columns: string[]; createdAt: number }

export const DEFAULTS: Settings = { baseUrl: 'http://127.0.0.1:8080/v1', key: '', model: 'local', maxSteps: 40, confirm: true }
const INDEX_MAX = 20

export async function getSettings(): Promise<Settings> {
  const { settings } = await chrome.storage.local.get('settings')
  return { ...DEFAULTS, ...(settings || {}) }
}
export const setSettings = (s: Settings) => chrome.storage.local.set({ settings: s })

export async function saveRun(run: Run) {
  await chrome.storage.local.set({ [`runs:${run.id}`]: run })
  const { runIndex = [] } = await chrome.storage.local.get('runIndex')
  if (!runIndex.includes(run.id)) {
    runIndex.unshift(run.id)
    const dropped = runIndex.splice(INDEX_MAX)
    await chrome.storage.local.set({ runIndex })
    if (dropped.length) await chrome.storage.local.remove(dropped.map((id: string) => `runs:${id}`))
  }
}
export async function endRun(run: Run) {
  run.messages = []  // keep rows and the summary, drop the transcript
  await chrome.storage.local.set({ [`runs:${run.id}`]: run })
}
export async function getRun(id: string): Promise<Run | undefined> {
  const got = (await chrome.storage.local.get(`runs:${id}`)) as unknown as Record<string, Run>
  return got[`runs:${id}`]
}
export async function listRuns(): Promise<Run[]> {
  const { runIndex = [] } = await chrome.storage.local.get('runIndex')
  const keys = runIndex.map((id: string) => `runs:${id}`)
  const got = (await chrome.storage.local.get(keys)) as unknown as Record<string, Run>
  return runIndex.map((id: string) => got[`runs:${id}`]).filter(Boolean)
}
