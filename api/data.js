// Your library, stored per-account so it syncs across devices.
// GET  -> { items, views, context }
// PUT  -> merge any of { items, views, context } and save.
const L = require('./_lib');

module.exports = async (req, res) => {
  if (!L.configured()) { L.json(res, 503, { error: 'not configured' }); return; }
  const email = L.sessionEmail(req);
  if (!email) { L.json(res, 401, { error: 'sign in' }); return; }

  const blob = await L.loadUser(email);
  if (req.method === 'GET') {
    L.json(res, 200, { items: blob.items || [], views: blob.views || [], context: blob.context || {}, updatedAt: blob.updatedAt || 0 });
    return;
  }
  if (req.method === 'PUT' || req.method === 'POST') {
    const b = await L.body(req);
    if (Array.isArray(b.items)) blob.items = b.items;
    if (Array.isArray(b.views)) blob.views = b.views;
    if (b.context && typeof b.context === 'object') blob.context = b.context;
    await L.saveUser(email, blob);
    L.json(res, 200, { ok: true, updatedAt: blob.updatedAt });
    return;
  }
  L.json(res, 405, { error: 'method' });
};
