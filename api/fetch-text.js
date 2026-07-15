// Phase 3 — auto-read an open-access paper the moment it's added.
// Server-side (avoids CORS) full-text fetch, no PDF parsing needed:
//   arXiv  -> ar5iv HTML (full text) -> strip tags; fallback: arXiv API abstract
//   PMC    -> BioC JSON (full text)
//   DOI    -> Crossref abstract (partial, better than nothing)
// Stateless + public papers only, so it needs no auth. Returns { ok, via, chars, text }.
const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36';

async function get(url, timeout = 22000) {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), timeout);
  try {
    const r = await fetch(url, { headers: { 'user-agent': UA }, signal: c.signal });
    if (!r.ok) return '';
    return await r.text();
  } catch (e) { return ''; } finally { clearTimeout(t); }
}
function strip(html) {
  html = html.replace(/<script[\s\S]*?<\/script>/gi, ' ').replace(/<style[\s\S]*?<\/style>/gi, ' ');
  const m = html.match(/<article[\s\S]*?<\/article>/i) || html.match(/<body[\s\S]*?<\/body>/i);
  let body = (m ? m[0] : html).replace(/<[^>]+>/g, ' ');
  try { body = body.replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n)).replace(/&[a-z]+;/gi, ' '); } catch (e) {}
  return body.replace(/\s+/g, ' ').trim();
}

module.exports = async (req, res) => {
  const url = (new URL(req.url, 'https://x').searchParams.get('url') || '').trim();
  const send = (o) => { res.setHeader('content-type', 'application/json'); res.end(JSON.stringify(o)); };
  if (!/^https?:\/\//.test(url)) { send({ ok: false, error: 'bad url' }); return; }
  const low = url.toLowerCase();
  const arx = (low.match(/arxiv\.org\/(?:abs|pdf)\/(\d{4}\.\d{4,5})/) || low.match(/(\d{4}\.\d{4,5})/) )?.[1];
  const pmc = (url.match(/PMC(\d+)/i) || [])[1];
  const doi = (url.match(/10\.\d{4,9}\/[^\s"'?#<>]+/) || [])[0];

  let text = '', via = '';
  // 1. arXiv full text via ar5iv
  if (!text && arx && low.includes('arxiv')) {
    const h = await get('https://ar5iv.labs.arxiv.org/html/' + arx);
    const t = strip(h);
    if (t.length > 2000) { text = t; via = 'ar5iv (full text)'; }
    if (!text) { // fallback: abstract
      const x = await get('https://export.arxiv.org/api/query?id_list=' + arx, 15000);
      const mm = x.match(/<summary>([\s\S]*?)<\/summary>/);
      if (mm) { text = mm[1].replace(/\s+/g, ' ').trim(); via = 'arXiv abstract'; }
    }
  }
  // 2. PMC full text via BioC
  if (!text && pmc) {
    const js = await get('https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC' + pmc + '/unicode');
    try {
      const parts = [];
      for (const d of (JSON.parse(js)[0].documents || [])) for (const p of (d.passages || [])) { const t = (p.text || '').trim(); if (t) parts.push(t); }
      const t = parts.join('\n');
      if (t.length > 2000) { text = t; via = 'PMC (full text)'; }
    } catch (e) {}
  }
  // 3. DOI abstract via Crossref
  if (!text && doi) {
    const js = await get('https://api.crossref.org/works/' + doi.replace(/[.)]+$/, ''), 15000);
    try {
      const a = JSON.parse(js).message.abstract;
      if (a) { text = a.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(); via = 'Crossref abstract'; }
    } catch (e) {}
  }
  send({ ok: text.length > 200, via, chars: text.length, text: text.slice(0, 55000) });
};
