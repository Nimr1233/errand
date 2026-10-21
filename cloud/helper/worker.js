// The website helper: a chat box on your own site that answers from your site's facts, through a
// free Cloudflare Worker that holds the Gemini key as a secret (the key never reaches a visitor).
// Rules (Gemini API terms, reports/Full feature free Errand plan.md):
// - visitors in the EU/EEA, the UK and Switzerland may only use paid Gemini: the helper is hidden there
// - not for under-18s; visitors are told chats go to Google and may be read by its reviewers
// - a hard daily cap, because it shares the one Gemini allowance with Errand
//
//   POST /ask {"question": "..."} -> {"answer": "..."}
//   env: GEMINI_KEY (secret), FACTS (your site's facts, plain text), DAILY_CAP (default 100), DB (D1)

const PAID_ONLY = new Set(['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV',
  'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'IS', 'LI', 'NO', 'GB', 'CH']);
const GEMINI = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions';

const reply = (data, status, origin) => new Response(JSON.stringify(data), {status, headers: {
  'content-type': 'application/json', 'access-control-allow-origin': origin || '*', 'access-control-allow-headers': 'content-type'}});

export default {
  async fetch(request, env) {
    const origin = env.SITE_ORIGIN;  // your site's address, so other sites can't use your allowance
    if (request.method === 'OPTIONS') return reply({}, 204, origin);
    if (new URL(request.url).pathname !== '/ask' || request.method !== 'POST') return reply({error: 'not found'}, 404, origin);
    if (origin && request.headers.get('origin') !== origin) return reply({error: 'not from this site'}, 403, origin);
    const country = (request.cf && request.cf.country) || '';
    if (PAID_ONLY.has(country)) return reply({error: 'The helper is not available in your region.'}, 451, origin);
    let question = '';
    try { question = String((await request.json()).question || '').slice(0, 500).trim(); } catch {}
    if (!question) return reply({error: 'ask a question'}, 400, origin);

    const day = new Date().toISOString().slice(0, 10);
    await env.DB.prepare('insert into usage (day, n) values (?, 0) on conflict(day) do nothing').bind(day).run();
    const used = (await env.DB.prepare('select n from usage where day = ?').bind(day).first()).n;
    if (used >= Number(env.DAILY_CAP || 100)) return reply({error: 'The helper has answered enough for today.'}, 429, origin);
    await env.DB.prepare('update usage set n = n + 1 where day = ?').bind(day).run();

    const r = await fetch(GEMINI, {method: 'POST', headers: {'content-type': 'application/json', authorization: `Bearer ${env.GEMINI_KEY}`},
      body: JSON.stringify({model: 'gemini-3.5-flash-lite', reasoning_effort: 'low', max_tokens: 300, messages: [
        {role: 'system', content: 'You answer visitors of one website, only from these facts. If the facts do not say, ' +
          `say you don't know. Never ask for personal details.\n\nFacts:\n${env.FACTS || ''}`},
        {role: 'user', content: question}]})});
    if (!r.ok) return reply({error: 'The helper could not answer right now.'}, 502, origin);
    const data = await r.json();
    return reply({answer: ((data.choices || [])[0] || {}).message?.content || "I don't know."}, 200, origin);
  },
};
