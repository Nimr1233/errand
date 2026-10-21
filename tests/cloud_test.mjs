// The two Cloudflare Workers, run under plain Node with a stand-in D1 database and a stand-in Gemini.
// Run by tests/test_cloud.py; exits non-zero on the first failed check.
import assert from 'node:assert/strict';
import inbox from '../cloud/inbox/worker.js';
import helper from '../cloud/helper/worker.js';

function fakeDB() {
  const events = [], usage = {};
  let id = 0;
  return {events, usage, prepare(sql) {
    const q = {a: [], bind(...a) { q.a = a; return q; },
      async run() {
        if (sql.startsWith('insert into events')) events.push({id: ++id, name: q.a[0], body: q.a[1], received: q.a[2]});
        else if (sql.startsWith('delete from events')) { const i = events.findIndex(e => e.id === q.a[0]); if (i >= 0) events.splice(i, 1); }
        else if (sql.startsWith('insert into usage')) usage[q.a[0]] ??= 0;
        else if (sql.startsWith('update usage')) usage[q.a[0]]++;
        return {};
      },
      async all() { return {results: events.slice(0, 50)}; },
      async first() { return {n: usage[q.a[0]]}; }};
    return q;
  }};
}

const S = 'test-secret-1234567890';
const env = {SECRET: S, DB: fakeDB()};
const call = (path, init = {}) => inbox.fetch(new Request('https://inbox.example' + path, init), env);

// a service posts a job request
let r = await call('/hook/price-check', {method: 'POST', headers: {'x-errand-secret': 'wrong'}, body: '{}'});
assert.equal(r.status, 401);
r = await call('/hook/price-check', {method: 'POST', headers: {'x-errand-secret': S}, body: 'not json'});
assert.equal(r.status, 400);
r = await call('/hook/price-check', {method: 'POST', headers: {'x-errand-secret': S}, body: JSON.stringify({skill: 'laptop price', urls: ['https://a.example/1']})});
assert.equal(r.status, 200);
r = await call('/hook/x', {method: 'POST', headers: {'x-errand-secret': S}, body: 'x'.repeat(40000)});
assert.equal(r.status, 413);
// the laptop collects, then acknowledges
assert.equal((await call('/events')).status, 401);
const got = await (await call('/events', {headers: {authorization: 'Bearer ' + S}})).json();
assert.equal(got.length, 1);
assert.equal(JSON.parse(got[0].body).skill, 'laptop price');
r = await call('/events/ack', {method: 'POST', headers: {authorization: 'Bearer ' + S}, body: JSON.stringify({ids: [got[0].id]})});
assert.deepEqual(await r.json(), {ok: true, deleted: 1});
assert.equal(env.DB.events.length, 0);

// the website helper
const asked = [];
globalThis.fetch = async (url, init) => { asked.push(JSON.parse(init.body)); return new Response(JSON.stringify({choices: [{message: {content: 'We open at 9.'}}]})); };
const henv = {GEMINI_KEY: 'k', FACTS: 'Open 9 to 5.', DAILY_CAP: '2', SITE_ORIGIN: 'https://shop.example', DB: fakeDB()};
const ask = (country, origin = 'https://shop.example', q = 'When do you open?') => {
  const req = new Request('https://helper.example/ask', {method: 'POST', headers: {origin, 'content-type': 'application/json'}, body: JSON.stringify({question: q})});
  Object.defineProperty(req, 'cf', {value: {country}});
  return helper.fetch(req, henv);
};
assert.equal((await ask('GB')).status, 451);  // UK: paid Gemini only, so hidden
assert.equal((await ask('DE')).status, 451);  // EU
assert.equal((await ask('CH')).status, 451);  // Switzerland
assert.equal((await ask('US', 'https://other.example')).status, 403);  // another site can't use your allowance
r = await ask('PK');
assert.equal(r.status, 200);
assert.equal((await r.json()).answer, 'We open at 9.');
assert.ok(asked[0].messages[0].content.includes('Open 9 to 5.'));  // it answers from your facts
assert.equal(asked[0].model, 'gemini-3.5-flash-lite');
assert.equal((await ask('US')).status, 200);
assert.equal((await ask('US')).status, 429);  // the daily cap
assert.equal(asked.length, 2);
console.log('cloud workers ok');
