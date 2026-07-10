// Your Anthropic key, stored encrypted at rest and returned only to you when signed in.
// GET    -> { hasKey, key }   (key decrypted for the authed owner; same posture as today's BYO key)
// PUT    -> { apiKey } -> encrypt + store
// DELETE -> remove
const L = require('./_lib');

module.exports = async (req, res) => {
  if (!L.configured()) { L.json(res, 503, { error: 'not configured' }); return; }
  const email = L.sessionEmail(req);
  if (!email) { L.json(res, 401, { error: 'sign in' }); return; }
  const blob = await L.loadUser(email);

  if (req.method === 'GET') {
    let key = '';
    if (blob.key) { try { key = L.decrypt(blob.key); } catch (e) { key = ''; } }
    L.json(res, 200, { hasKey: !!key, key });
    return;
  }
  if (req.method === 'PUT' || req.method === 'POST') {
    const b = await L.body(req);
    const apiKey = (b.apiKey || '').trim();
    if (!apiKey.startsWith('sk-')) { L.json(res, 400, { error: 'Provide an Anthropic key that starts with sk-' }); return; }
    blob.key = L.encrypt(apiKey);
    await L.saveUser(email, blob);
    L.json(res, 200, { ok: true });
    return;
  }
  if (req.method === 'DELETE') {
    blob.key = '';
    await L.saveUser(email, blob);
    L.json(res, 200, { ok: true });
    return;
  }
  L.json(res, 405, { error: 'method' });
};
