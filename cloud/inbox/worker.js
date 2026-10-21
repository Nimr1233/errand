// Errand's webhook inbox: a free Cloudflare Worker with a D1 table. The only part of Errand that is
// always online. Outside services post job requests here at any hour; the laptop collects them about
// once a minute while Errand runs (errand/inbox.py) and deletes what it has handled.
// Free tier: 100,000 requests and 100,000 D1 rows written a day, 10 ms of CPU per request.
//
//   POST /hook/<name>   from a service, with header X-Errand-Secret: <secret>
//                       body: {"skill": "...", "urls": [...], "values": {...}}
//   GET  /events        from the laptop, Authorization: Bearer <secret>: up to 50 waiting events
//   POST /events/ack    from the laptop, {"ids": [...]}: delete handled events

const MAX_BODY = 32 * 1024;

const same = (a, b) => {  // a constant-time compare, so the secret can't be guessed letter by letter
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
};
const json = (data, status = 200) => new Response(JSON.stringify(data), {status, headers: {'content-type': 'application/json'}});

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const hook = url.pathname.match(/^\/hook\/([\w-]{1,40})$/);
    if (hook && request.method === 'POST') {
      if (!same(request.headers.get('x-errand-secret') || '', env.SECRET)) return json({error: 'wrong secret'}, 401);
      const body = await request.text();
      if (body.length > MAX_BODY) return json({error: 'too big'}, 413);
      try { JSON.parse(body); } catch { return json({error: 'send JSON'}, 400); }
      await env.DB.prepare('insert into events (name, body, received) values (?, ?, ?)')
        .bind(hook[1], body, new Date().toISOString()).run();
      return json({ok: true});
    }
    if (!same((request.headers.get('authorization') || '').replace(/^Bearer /, ''), env.SECRET)) return json({error: 'wrong secret'}, 401);
    if (url.pathname === '/events' && request.method === 'GET') {
      const {results} = await env.DB.prepare('select id, name, body, received from events order by id limit 50').all();
      return json(results);
    }
    if (url.pathname === '/events/ack' && request.method === 'POST') {
      const ids = ((await request.json()).ids || []).filter(Number.isInteger).slice(0, 50);
      for (const id of ids) await env.DB.prepare('delete from events where id = ?').bind(id).run();
      return json({ok: true, deleted: ids.length});
    }
    return json({error: 'not found'}, 404);
  },
};
