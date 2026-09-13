// Static vector derivative only: no HTML execution, browser launch, or external resources.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require('/Users/noahsutter/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root = path.resolve(__dirname, '../../..');
const fingerprint = p => {
  const bytes = fs.readFileSync(p);
  return { path: path.relative(root, p), bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') };
};
const escapeXml = text => text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

(async () => {
  for (const edition of ['live', 'slide']) {
    const stem = `kirocrew-arm-${edition}`;
    const htmlPath = path.join(root, `${stem}.html`);
    const specPath = path.join(root, `${stem}.architecture.json`);
    const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
    const html = fs.readFileSync(htmlPath, 'utf8');
    let svg = html.match(/<svg\b[\s\S]*?<\/svg>/)[0];
    const fullCss = [...html.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)].map(match => match[1]).join('\n');
    const theme = fullCss.match(/\[data-theme="light"\]\s*\{([\s\S]*?)\}/)[1];
    const values = Object.fromEntries([...theme.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map(match => [match[1], match[2].trim()]));
    let css = fullCss.replace(/var\((--[\w-]+)\)/g, (all, name) => values[name] || all);
    css += '\nsvg { font-family: ' + fullCss.match(/font-family:\s*([^;]*ui-monospace[^;]*);/)[1] + '; }';
    if (/@import|url\(\s*["']?(?:https?:|file:)/.test(css)) throw Error('External stylesheet resources prohibited');
    if (/<script|<foreignObject|\b(?:href|xlink:href)=["'](?:https?:|file:)/.test(svg)) throw Error('Executable or external SVG prohibited');
    const viewBox = svg.match(/viewBox="([^"]+)"/)[1].split(/\s+/).map(Number);
    const [width, height] = viewBox.slice(2);
    svg = svg.replace('<svg ', `<svg xmlns="http://www.w3.org/2000/svg" data-theme="light" width="${width}" height="${height}" `)
      .replace(/(<svg\b[^>]*>)/, `$1<style><![CDATA[${css}]]></style><rect width="${width}" height="${height}" fill="${values['--bg']}"/>`);
    let annotation = null;
    if (edition === 'slide') {
      const card = spec.cards.find(card => card.title === 'Evidence boundary');
      const expected = ['Verified direct probe: mcp-demo → MCP → S3.', 'Native Kiro CLI path pending sign-in.'];
      if (JSON.stringify(card.items) !== JSON.stringify(expected)) throw Error('Evidence footer source changed; inspect before export');
      const baselines = [246, 265];
      const footer = `<g id="presentation-evidence-footer" aria-label="Evidence boundary">${card.items.map((line, index) => `<text x="360" y="${baselines[index]}" text-anchor="middle" font-size="11" font-weight="500" fill="#334155">${escapeXml(line)}</text>`).join('')}</g>`;
      svg = svg.replace('</svg>', footer + '</svg>');
      annotation = { source: 'cards[0].items', text: card.items, x: 360, baselines, fontSizeSvgUnits: 11, purpose: 'Copy the authored HTML evidence card into unused SVG footer space so the standalone slide image carries the same verification boundary. Existing node, boundary and route geometry is unchanged.' };
    }
    const svgPath = path.join(__dirname, `${stem}-council.svg`);
    const pngPath = path.join(__dirname, `${stem}-council.png`);
    const actualPath = path.join(__dirname, `${stem}-council-1152x480.png`);
    fs.writeFileSync(svgPath, svg);
    await sharp(Buffer.from(svg)).resize({ width: width * 3, height: height * 3, fit: 'contain', background: '#ffffff' }).png().toFile(pngPath);
    await sharp(Buffer.from(svg)).resize({ width: 1152, height: 480, fit: 'contain', background: '#ffffff' }).png().toFile(actualPath);
    const receipt = {
      time: new Date().toISOString(), kind: 'non-browser-static-graphics-render',
      source: fingerprint(htmlPath), specification: fingerprint(specPath), rendererScript: fingerprint(__filename),
      svg: fingerprint(svgPath), png: fingerprint(pngPath), actualSize: fingerprint(actualPath),
      authoredViewBox: viewBox, annotation, renderer: sharp.versions,
      method: 'Extract authored SVG from delivered HTML; embed its generated stylesheet with light-theme variables resolved and restore body font inheritance. For the slide derivative only, transcribe the authored evidence card into unused footer space. Render through libvips/librsvg; no HTML JavaScript or browser execution.',
      limitations: ['Static graphics rendering does not validate the HTML viewer, interactions, themes, or browser containment.', 'CUA file URL policy blocked browser navigation; no browser/server reroute was attempted.']
    };
    fs.writeFileSync(path.join(__dirname, `${stem}-council-static.json`), JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify({ edition, svg: receipt.svg, png: receipt.png, actualSize: receipt.actualSize }));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
