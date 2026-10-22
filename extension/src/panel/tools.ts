// The tools the model may call (spec section 5): our own names and schemas. Each has a JSON Schema for the
// model and a zod schema the loop checks the input against before running it. strict + no extra properties.
import { z } from 'zod'

export type ToolDef = { name: string; description: string; parameters: object }

const el = { id: { type: 'string', description: 'element id from the snapshot, like f0:12' } }
const strict = (properties: object, required: string[]) =>
  ({ type: 'object', additionalProperties: false, properties, required })

export const TOOLS: ToolDef[] = [
  { name: 'click', description: 'Click an element.', parameters: strict({ ...el, mode: { type: 'string', enum: ['single', 'double', 'right', 'hover'] }, irreversible: { type: 'boolean' } }, ['id']) },
  { name: 'type', description: 'Type text into a field.', parameters: strict({ ...el, text: { type: 'string' }, clear: { type: 'boolean' }, submit: { type: 'boolean' }, irreversible: { type: 'boolean' } }, ['id', 'text']) },
  { name: 'select_option', description: 'Choose an option in a dropdown.', parameters: strict({ ...el, value: { type: 'string' } }, ['id', 'value']) },
  { name: 'press_key', description: 'Press a key.', parameters: strict({ key: { type: 'string' }, id: { type: 'string' } }, ['key']) },
  { name: 'scroll', description: 'Scroll the page or an element.', parameters: strict({ id: { type: 'string' }, direction: { type: 'string', enum: ['up', 'down'] }, amount: { type: 'string', enum: ['page', 'end'] } }, ['direction']) },
  { name: 'wait_for', description: 'Wait until text or an element appears.', parameters: strict({ text: { type: 'string' }, id: { type: 'string' }, timeout_ms: { type: 'number' } }, ['timeout_ms']) },
  { name: 'goto_url', description: 'Go to a URL (http/https only).', parameters: strict({ url: { type: 'string' } }, ['url']) },
  { name: 'tab', description: 'Open, switch or close a tab.', parameters: strict({ action: { type: 'string', enum: ['open', 'switch', 'close'] }, url: { type: 'string' }, tab_id: { type: 'number' } }, ['action']) },
  { name: 'save_rows', description: 'Append rows to the results table.', parameters: strict({ columns: { type: 'array', items: { type: 'string' } }, rows: { type: 'array', items: { type: 'array', items: { type: 'string' } } } }, ['columns', 'rows']) },
  { name: 'answer_task', description: 'Finish the task with an answer.', parameters: strict({ text: { type: 'string' } }, ['text']) },
  { name: 'ask_user', description: 'Pause and ask the user a question.', parameters: strict({ question: { type: 'string' } }, ['question']) },
]

const SCHEMAS: Record<string, z.ZodTypeAny> = {
  click: z.object({ id: z.string(), mode: z.enum(['single', 'double', 'right', 'hover']).optional(), irreversible: z.boolean().optional() }).strict(),
  type: z.object({ id: z.string(), text: z.string(), clear: z.boolean().optional(), submit: z.boolean().optional(), irreversible: z.boolean().optional() }).strict(),
  select_option: z.object({ id: z.string(), value: z.string() }).strict(),
  press_key: z.object({ key: z.string(), id: z.string().optional() }).strict(),
  scroll: z.object({ id: z.string().optional(), direction: z.enum(['up', 'down']), amount: z.enum(['page', 'end']).optional() }).strict(),
  wait_for: z.object({ text: z.string().optional(), id: z.string().optional(), timeout_ms: z.number().max(10000) }).strict(),
  goto_url: z.object({ url: z.string().regex(/^https?:\/\//) }).strict(),
  tab: z.object({ action: z.enum(['open', 'switch', 'close']), url: z.string().optional(), tab_id: z.number().optional() }).strict(),
  save_rows: z.object({ columns: z.array(z.string()), rows: z.array(z.array(z.string())) }).strict(),
  answer_task: z.object({ text: z.string() }).strict(),
  ask_user: z.object({ question: z.string() }).strict(),
}

export function validate(name: string, input: unknown): { ok: true; value: any } | { ok: false; error: string } {
  const schema = SCHEMAS[name]
  if (!schema) return { ok: false, error: `unknown tool ${name}` }
  const r = schema.safeParse(input)
  return r.success ? { ok: true, value: r.data } : { ok: false, error: r.error.issues.map(i => i.path.join('.') + ' ' + i.message).join('; ') }
}

// Confirm gate (spec section 5): irreversible flag, or a name that matches a dangerous verb.
const DANGER = /\b(buy|pay|order|checkout|purchase|send|submit|post|publish|delete|remove|transfer|confirm|login|log ?in|sign ?in|sign ?up|register)\b/i
export function needsConfirm(name: string, input: any, targetName = ''): boolean {
  const acts = name === 'click' || (name === 'type' && input?.submit) || (name === 'press_key' && input?.key === 'Enter')
  if (!acts) return false
  return input?.irreversible === true || DANGER.test(targetName)
}
