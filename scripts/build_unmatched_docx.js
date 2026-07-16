// Build docs/unmatched_linkedin_sources.docx from docs/unmatched_linkedin.json
const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, BorderStyle } = require('docx');

const entries = JSON.parse(fs.readFileSync(__dirname + '/../docs/unmatched_linkedin.json', 'utf8'));
const withLink = entries.filter(e => e.links.length).length;

const children = [
  new Paragraph({ heading: HeadingLevel.HEADING_1,
    children: [new TextRun('Unmatched LinkedIn posts — 7/4 source dump (verbatim)')] }),
  new Paragraph({ spacing: { after: 160 }, children: [ new TextRun({
    text: `${entries.length} posts from the source dump that didn't map to an existing Stacks item. `
        + `Each post below is reproduced verbatim so you can Ctrl-F any line to find the original. `
        + `Links each post carried are listed first (resolved destination where the lnkd.in shortener `
        + `could be followed, otherwise the shortener itself). ${withLink} carry a link; ${entries.length - withLink} do not.`,
    italics: true, color: '666666', size: 20 }) ] }),
];

for (const e of entries) {
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240 },
    children: [new TextRun(`${e.n}. ${e.name}`)] }));
  children.push(new Paragraph({ spacing: { after: 80 }, children: [
    new TextRun({ text: 'Links: ', bold: true, size: 20 }),
    new TextRun({ text: e.links.length ? e.links.join('   ·   ') : '(none — Ctrl-F the text below)',
      color: e.links.length ? '1155CC' : '999999', size: 20 }),
  ] }));
  for (const line of e.body) {
    children.push(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: line, size: 21 })] }));
  }
  children.push(new Paragraph({ spacing: { before: 120, after: 120 },
    border: { bottom: { color: 'DDDDDD', space: 1, style: BorderStyle.SINGLE, size: 6 } }, children: [] }));
}

const doc = new Document({
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 } } }, children }],
});
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(__dirname + '/../docs/unmatched_linkedin_sources.docx', buf);
  console.log('wrote docs/unmatched_linkedin_sources.docx (' + entries.length + ' posts)');
});
