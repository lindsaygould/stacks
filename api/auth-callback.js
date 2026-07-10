// Google redirects back here: verify CSRF state, exchange the code for a verified
// email, check the allowlist, and start a session. Then send the user to the app.
const L = require('./_lib');

function fail(res, msg) {
  res.statusCode = 302;
  res.setHeader('Location', '/?login=' + encodeURIComponent(msg));
  res.end();
}

module.exports = async (req, res) => {
  if (!L.configured()) { fail(res, 'unconfigured'); return; }
  const url = new URL(req.url, 'https://x');
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  const expected = L.cookies(req)['stacks_oauth'];
  L.clearCookie(res, 'stacks_oauth');
  if (!code || !state || !expected || state !== expected) { fail(res, 'state'); return; }

  let email = null;
  try { email = await L.googleExchange(req, code); } catch (e) { email = null; }
  if (!email) { fail(res, 'exchange'); return; }
  if (!L.allowed(email)) { fail(res, 'not_allowed'); return; }

  L.setCookie(res, L.COOKIE, L.makeSession(email));
  res.statusCode = 302;
  res.setHeader('Location', '/');
  res.end();
};
