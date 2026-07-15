// Google Drive consent redirects back here: verify state, exchange the code for a
// refresh token, and store it (encrypted) on the user so the app can read Drive later.
const L = require('./_lib');

function done(res, msg) {
  res.statusCode = 302;
  res.setHeader('Location', '/?drive=' + encodeURIComponent(msg));
  res.end();
}

module.exports = async (req, res) => {
  if (!L.configured()) { done(res, 'unconfigured'); return; }
  const email = L.sessionEmail(req);
  if (!email) { done(res, 'signin'); return; }
  const url = new URL(req.url, 'https://x');
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const expected = L.cookies(req)['drive_oauth'];
  L.clearCookie(res, 'drive_oauth');
  if (!code || !state || state !== expected) { done(res, 'state'); return; }

  let tok = null;
  try { tok = await L.driveExchange(req, code); } catch (e) { tok = null; }
  if (!tok || !tok.refresh_token) { done(res, 'noaccess'); return; }

  const blob = await L.loadUser(email);
  blob.driveRefresh = L.encrypt(tok.refresh_token);
  await L.saveUser(email, blob);
  done(res, 'connected');
};
