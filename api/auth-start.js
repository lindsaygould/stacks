// Kick off "Sign in with Google": set a short-lived CSRF state cookie, redirect to consent.
const L = require('./_lib');
const crypto = require('crypto');

module.exports = async (req, res) => {
  if (!L.configured()) { L.json(res, 503, { error: 'login not configured' }); return; }
  const state = crypto.randomBytes(16).toString('hex');
  L.setCookie(res, 'stacks_oauth', state, 600); // 10 min
  res.statusCode = 302;
  res.setHeader('Location', L.googleAuthUrl(req, state));
  res.end();
};
