// Read PDFs from your Drive "Papers" folder and extract text for the paywalled papers
// that need it. The client posts the papers still needing a PDF (id/title/url/ident);
// we match each Drive PDF by identifier or title, parse it, and return the text to store.
// Capped per call so it stays within the function time limit — call again for the rest.
const L = require('./_lib');
let pdfParse = null;
try { pdfParse = require('pdf-parse/lib/pdf-parse.js'); } catch (e) { pdfParse = null; }

const CAP = 3; // PDFs parsed per call — small so we stay under the function time limit; call again for more
const norm = (s) => (s || '').toLowerCase();
const idTok = (s) => (norm(s).match(/\d{4}\.\d{4,5}/) || [''])[0];
const words = (s) => new Set(norm(s).replace(/\.pdf$/, '').split(/[^a-z0-9]+/).filter((w) => w.length > 3));
function matchItem(items, fname) {
  const ft = idTok(fname), fw = words(fname);
  for (const it of items) { const at = idTok((it.url || '') + ' ' + (it.ident || '')); if (at && ft && at === ft) return it; }
  let best = null, bs = 0;
  for (const it of items) { const iw = words(it.title); if (iw.size < 4) continue; let c = 0; for (const w of iw) if (fw.has(w)) c++; const s = c / iw.size; if (s > bs) { bs = s; best = it; } }
  return bs >= 0.5 ? best : null;
}

module.exports = async (req, res) => {
  if (!L.configured()) { L.json(res, 503, { error: 'not configured' }); return; }
  const email = L.sessionEmail(req);
  if (!email) { L.json(res, 401, { error: 'sign in' }); return; }
  const blob = await L.loadUser(email);
  if (!blob.driveRefresh) { L.json(res, 200, { connected: false }); return; }
  if (!pdfParse) { L.json(res, 500, { error: 'pdf parser unavailable' }); return; }

  const b = await L.body(req);
  const items = Array.isArray(b.items) ? b.items.slice(0, 4000) : [];
  const access = await L.driveAccess(L.decrypt(blob.driveRefresh));
  if (!access) { L.json(res, 200, { connected: false, error: 'reconnect' }); return; }

  const folderId = (await L.driveFindFolder(access, 'Papers')) || (await L.driveFindFolder(access, 'The Stacks'));
  if (!folderId) { L.json(res, 200, { connected: true, folder: false, error: 'No Drive folder named "Papers" found — create one and drop PDFs in it.' }); return; }

  const pdfs = await L.driveListPdfs(access, folderId);
  const results = [];
  let matchedTotal = 0;
  for (const f of pdfs) {
    const it = matchItem(items, f.name);
    if (!it) continue;
    matchedTotal++;
    if (results.length >= CAP) continue;
    const buf = await L.driveDownload(access, f.id);
    if (!buf) continue;
    let text = '';
    try { const d = await pdfParse(buf); text = (d.text || '').trim(); } catch (e) { text = ''; }
    if (text.length > 1500) results.push({ id: it.id, chars: text.length, filename: f.name, text: text.slice(0, 55000) });
  }
  L.json(res, 200, { connected: true, folder: true, folderPdfs: pdfs.length, matched: matchedTotal, synced: results.length, remaining: Math.max(0, matchedTotal - results.length), results });
};
