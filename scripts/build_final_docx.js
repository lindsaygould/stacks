// Build docs/new_sources_to_add.docx from docs/unmatched_final.json (the 55 genuinely-new posts)
const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, BorderStyle } = require('docx');
const entries = JSON.parse(fs.readFileSync(__dirname + '/../docs/unmatched_final.json', 'utf8'));
const withLink = entries.filter(e => e.links.length).length;

const children = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('New sources to add — from the 7/4 LinkedIn dump')] }),
  new Paragraph({ spacing: { after: 160 }, children: [ new TextRun({
    text: `${entries.length} posts that are genuinely NOT yet in Stacks (after three matching passes removed the 47 that already exist). `
        + `Each is reproduced verbatim so you can Ctrl-F it in the original. Links it carried are listed first. `
        + `${withLink} carry a link; ${entries.length - withLink} do not.`,
    italics: true, color: '666666', size: 20 }) ] }),
];
for (const e of entries) {
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240 }, children: [new TextRun(`${e.n}. ${e.name}`)] }));
  children.push(new Paragraph({ spacing: { after: 80 }, children: [
    new TextRun({ text: 'Links: ', bold: true, size: 20 }),
    new TextRun({ text: e.links.length ? e.links.join('   ·   ') : '(none — Ctrl-F the text below)', color: e.links.length ? '1155CC' : '999999', size: 20 }),
  ] }));
  for (const line of e.body) children.push(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: line, size: 21 })] }));
  children.push(new Paragraph({ spacing: { before: 120, after: 120 }, border: { bottom: { color: 'DDDDDD', space: 1, style: BorderStyle.SINGLE, size: 6 } }, children: [] }));
}
const doc = new Document({ sections: [{ properties: { page: { size: { width: 12240, height: 15840 } } }, children }] });
Packer.toBuffer(doc).then(buf => { fs.writeFileSync(__dirname + '/../docs/new_sources_to_add.docx', buf); console.log('wrote docs/new_sources_to_add.docx (' + entries.length + ' new sources)'); });
