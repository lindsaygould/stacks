// Who am I? Drives the frontend gate. Returns whether login is even available
// (configured) so the app can fall back to local mode when it isn't.
const L = require('./_lib');

module.exports = async (req, res) => {
  const cfg = L.configured();
  if (!cfg) { L.json(res, 200, { configured: false, signedIn: false }); return; }
  const email = L.sessionEmail(req);
  if (!email) { L.json(res, 200, { configured: true, signedIn: false }); return; }
  let hasKey = false;
  try { hasKey = !!(await L.loadUser(email)).key; } catch (e) {}
  L.json(res, 200, { configured: true, signedIn: true, email, hasKey });
};
