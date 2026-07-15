// Connect Google Drive (read-only) so the app can read PDFs you drop in your Papers folder.
// Signed-in users only. Sets a CSRF state cookie and redirects to Google's consent.
const L = require('./_lib');
const crypto = require('crypto');

module.exports = async (req, res) => {
  if (!L.configured()) { L.json(res, 503, { error: 'not configured' }); return; }
  const email = L.sessionEmail(req);
  if (!email) { L.json(res, 401, { error: 'sign in first' }); return; }
  const state = crypto.randomBytes(16).toString('hex');
  L.setCookie(res, 'drive_oauth', state, 600);
  res.statusCode = 302;
  res.setHeader('Location', L.driveAuthUrl(req, state));
  res.end();
};
