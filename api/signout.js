const L = require('./_lib');

module.exports = async (req, res) => {
  L.clearCookie(res, L.COOKIE);
  L.json(res, 200, { ok: true });
};
