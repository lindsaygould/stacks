// Read PDFs from your Drive "Stacks Papers" folder and match them to paywalled papers
// BY CONTENT (the title printed on the PDF's first page), not the filename — so you can
// drop PDFs in with whatever names they came with. Client posts the papers still needing
// a PDF; we parse each PDF, match, and return the text. Capped per call + resumable via `skip`.
const L = require('./_lib');
let pdfParse = null;
try { pdfParse = require('pdf-parse/lib/pdf-parse.js'); } catch (e) { pdfParse = null; }

const CAP = 3; // PDFs parsed per call (parsing is the slow part) — client loops with `skip` for the rest
const STOP = new Set('the a an of for and or in on with to from using via based by is are as at we our this that these those between within their its it new study effect effects role toward paper main pdf full using into over under about'.split(' '));
const words = (s) => new Set((s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').split(' ').filter((w) => w.length > 3 && !STOP.has(w)));
const idTok = (s) => ((s || '').toLowerCase().match(/\d{4}\.\d{4,5}/) || [''])[0];

// Match a PDF to the paper it is, using the text near its top (title/authors/abstract).
function matchByText(items, head) {
  const hw = new Set(head.toLowerCase().replace(/[^a-z0-9]+/g, ' ').split(' '));
  const hid = idTok(head);
  let best = null, bs = 0;
  for (const it of items) {
    const iid = idTok((it.url || '') + ' ' + (it.ident || ''));
    if (iid && hid && iid === hid) return it;              // arXiv id printed in the PDF
    const tw = words(it.title); if (tw.size < 4) continue;
    let c = 0; for (const w of tw) if (hw.has(w)) c++;
    const s = c / tw.size; if (s > bs) { bs = s; best = it; }
  }
  return bs >= 0.6 ? best : null;                          // ≥60% of the title's words appear up top
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
  const skip = new Set(Array.isArray(b.skip) ? b.skip : []);
  const access = await L.driveAccess(L.decrypt(blob.driveRefresh));
  if (!access) { L.json(res, 200, { connected: false, error: 'reconnect' }); return; }

  const folderId = (await L.driveFindFolder(access, 'Stacks Papers')) || (await L.driveFindFolder(access, 'Papers'));
  if (!folderId) { L.json(res, 200, { connected: true, folder: false, error: 'No Drive folder named "Stacks Papers" found — create one and drop PDFs in it.' }); return; }

  const all = await L.driveListPdfs(access, folderId);
  const todo = all.filter((f) => !skip.has(f.id));
  const results = [], processed = [];
  for (const f of todo) {
    if (processed.length >= CAP) break;
    processed.push(f.id);
    const buf = await L.driveDownload(access, f.id);
    if (!buf) continue;
    let text = '';
    try { const d = await pdfParse(buf); text = (d.text || '').trim(); } catch (e) { text = ''; }
    if (text.length < 1500) continue;
    const it = matchByText(items, text.slice(0, 4000));
    if (it) {
      results.push({ id: it.id, chars: text.length, filename: f.name, text: text.slice(0, 55000) });
      const i = items.findIndex((x) => x.id === it.id); if (i >= 0) items.splice(i, 1); // don't reassign
    }
  }
  const remaining = todo.length - processed.length;
  L.json(res, 200, { connected: true, folder: true, folderPdfs: all.length, synced: results.length, processedIds: processed, remaining, done: remaining <= 0, results });
};
