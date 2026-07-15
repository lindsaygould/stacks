const L = require('./_lib');
module.exports = async (req, res) => {
  if (!L.configured()) { L.json(res, 200, { configured: false }); return; }
  const email = L.sessionEmail(req);
  if (!email) { L.json(res, 401, { error: 'sign in' }); return; }
  const blob = await L.loadUser(email);
  L.json(res, 200, { configured: true, connected: !!blob.driveRefresh });
};
