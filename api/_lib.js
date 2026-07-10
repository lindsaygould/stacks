// Shared backend helpers for Stacks multi-device login + server-side storage.
// Dependency-free: node:crypto + global fetch (Node 18+ on Vercel) + Vercel KV REST.
// Mirrors the Kairos auth pattern: Google OAuth (auth-code) -> HMAC-signed session
// cookie -> per-user blob in KV, with the Anthropic key AES-256-GCM encrypted at rest.
const crypto = require('crypto');

const COOKIE = 'stacks_session';
const TTL = 30 * 24 * 60 * 60; // 30 days (seconds)

// The backend only activates when the essentials are present; otherwise the app
// stays in local (browser-only) mode. This is what makes login opt-in + safe pre-setup.
function configured() {
  return !!(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET &&
            process.env.SESSION_SECRET && process.env.ENCRYPTION_KEY &&
            process.env.KV_REST_API_URL && process.env.KV_REST_API_TOKEN);
}

function baseUrl(req) {
  if (process.env.APP_URL) return process.env.APP_URL.replace(/\/$/, '');
  const proto = req.headers['x-forwarded-proto'] || 'https';
  const host = req.headers['x-forwarded-host'] || req.headers.host;
  return proto + '://' + host;
}

// ---- cookies ----
function cookies(req) {
  const out = {};
  (req.headers.cookie || '').split(';').forEach(p => {
    const i = p.indexOf('='); if (i < 1) return;
    out[p.slice(0, i).trim()] = decodeURIComponent(p.slice(i + 1).trim());
  });
  return out;
}
function appendCookie(res, str) {
  const prev = res.getHeader('Set-Cookie') || [];
  res.setHeader('Set-Cookie', [].concat(prev, str));
}
function setCookie(res, name, val, maxAge = TTL) {
  appendCookie(res, `${name}=${encodeURIComponent(val)}; Path=/; HttpOnly; SameSite=Lax; Secure; Max-Age=${maxAge}`);
}
function clearCookie(res, name) {
  appendCookie(res, `${name}=; Path=/; HttpOnly; SameSite=Lax; Secure; Max-Age=0`);
}

// ---- session (HMAC-SHA256 signed, self-contained) ----
function hmac(payload) {
  return crypto.createHmac('sha256', process.env.SESSION_SECRET).update(payload).digest('hex');
}
function timingEq(a, b) {
  const ba = Buffer.from(a), bb = Buffer.from(b);
  return ba.length === bb.length && crypto.timingSafeEqual(ba, bb);
}
function makeSession(email) {
  const payload = Buffer.from(email).toString('base64url') + '.' + (Date.now() + TTL * 1000);
  return payload + '.' + hmac(payload);
}
function sessionEmail(req) {
  const v = cookies(req)[COOKIE];
  if (!v) return null;
  const parts = v.split('.');
  if (parts.length !== 3) return null;
  const payload = parts[0] + '.' + parts[1];
  if (!timingEq(parts[2], hmac(payload))) return null;
  if (Number(parts[1]) < Date.now()) return null;
  return Buffer.from(parts[0], 'base64url').toString('utf8').toLowerCase();
}

// ---- AES-256-GCM for the API key at rest ----
function encrypt(text) {
  const key = Buffer.from(process.env.ENCRYPTION_KEY, 'hex');
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ct = Buffer.concat([c.update(text, 'utf8'), c.final()]);
  return iv.toString('hex') + ':' + c.getAuthTag().toString('hex') + ':' + ct.toString('hex');
}
function decrypt(enc) {
  const [ivh, tagh, cth] = String(enc).split(':');
  const key = Buffer.from(process.env.ENCRYPTION_KEY, 'hex');
  const d = crypto.createDecipheriv('aes-256-gcm', key, Buffer.from(ivh, 'hex'));
  d.setAuthTag(Buffer.from(tagh, 'hex'));
  return Buffer.concat([d.update(Buffer.from(cth, 'hex')), d.final()]).toString('utf8');
}

// ---- Vercel KV (Upstash Redis) REST ----
async function kvGet(key) {
  const r = await fetch(`${process.env.KV_REST_API_URL}/get/${encodeURIComponent(key)}`,
    { headers: { Authorization: `Bearer ${process.env.KV_REST_API_TOKEN}` } });
  if (!r.ok) return null;
  const j = await r.json();
  return j.result == null ? null : j.result;
}
async function kvSet(key, val) {
  const r = await fetch(`${process.env.KV_REST_API_URL}/set/${encodeURIComponent(key)}`,
    { method: 'POST', headers: { Authorization: `Bearer ${process.env.KV_REST_API_TOKEN}` }, body: val });
  return r.ok;
}

// per-user blob: { items:[], views:[], context:{}, key:"<encrypted>", updatedAt }
async function loadUser(email) {
  const raw = await kvGet('user:' + email);
  if (!raw) return { items: [], views: [], context: {}, key: '' };
  try { return JSON.parse(raw); } catch (e) { return { items: [], views: [], context: {}, key: '' }; }
}
async function saveUser(email, blob) {
  blob.updatedAt = Date.now();
  return kvSet('user:' + email, JSON.stringify(blob));
}

// ---- Google OAuth (auth-code) ----
function googleAuthUrl(req, state) {
  const p = new URLSearchParams({
    client_id: process.env.GOOGLE_CLIENT_ID,
    redirect_uri: baseUrl(req) + '/api/auth-callback',
    response_type: 'code', scope: 'openid email profile',
    state, access_type: 'online', prompt: 'select_account',
  });
  return 'https://accounts.google.com/o/oauth2/v2/auth?' + p.toString();
}
async function googleExchange(req, code) {
  const r = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      code, client_id: process.env.GOOGLE_CLIENT_ID, client_secret: process.env.GOOGLE_CLIENT_SECRET,
      redirect_uri: baseUrl(req) + '/api/auth-callback', grant_type: 'authorization_code',
    }),
  });
  if (!r.ok) return null;
  const t = await r.json();
  if (!t.id_token) return null;
  // id_token came straight from Google's token endpoint over TLS -> safe to decode.
  const payload = JSON.parse(Buffer.from(t.id_token.split('.')[1], 'base64url').toString('utf8'));
  if (!payload.email || !payload.email_verified) return null;
  return payload.email.toLowerCase();
}

// Only allow listed accounts (comma-separated OWNER_EMAIL). Empty -> first-come is owner.
function allowed(email) {
  const list = (process.env.OWNER_EMAIL || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
  return list.length === 0 || list.includes(email);
}

function json(res, code, obj) {
  res.statusCode = code;
  res.setHeader('content-type', 'application/json');
  res.end(JSON.stringify(obj));
}
async function body(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  if (!chunks.length) return {};
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')); } catch (e) { return {}; }
}

module.exports = {
  COOKIE, configured, baseUrl, cookies, setCookie, clearCookie,
  makeSession, sessionEmail, encrypt, decrypt, loadUser, saveUser,
  googleAuthUrl, googleExchange, allowed, json, body,
};
