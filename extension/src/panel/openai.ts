// The one model adapter (spec section 7): an OpenAI-compatible chat endpoint. Default is the local brain
// server at 127.0.0.1:8080. The loop never sees provider formats.
import type { ToolDef } from './tools'

export type Msg = { role: 'system' | 'user' | 'assistant' | 'tool'; content: string; tool_call_id?: string; name?: string; tool_calls?: any[] }
export type Next = { toolCall?: { id: string; name: string; input: any }; text?: string; usage?: any }

export async function next(baseUrl: string, key: string, model: string, messages: Msg[], tools: ToolDef[], signal: AbortSignal): Promise<Next> {
  const res = await fetch(`${baseUrl.replace(/\/$/, '')}/chat/completions`, {
    method: 'POST', signal,
    headers: { 'content-type': 'application/json', ...(key ? { authorization: `Bearer ${key}` } : {}) },
    body: JSON.stringify({
      model, messages, tool_choice: 'auto', parallel_tool_calls: false,
      tools: tools.map(t => ({ type: 'function', function: { name: t.name, description: t.description, parameters: t.parameters } })),
    }),
  })
  if (res.status === 429 || res.status >= 500) throw Object.assign(new Error(`HTTP ${res.status}`), { retryable: true })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text().catch(() => '')}`)
  const data = await res.json()
  const msg = data.choices?.[0]?.message
  const call = msg?.tool_calls?.[0]
  if (call) {
    let input: any = {}
    try { input = JSON.parse(call.function.arguments || '{}') } catch { /* reported as a validation error upstream */ }
    return { toolCall: { id: call.id || 'call', name: call.function.name, input }, usage: data.usage }
  }
  return { text: msg?.content || '', usage: data.usage }
}
