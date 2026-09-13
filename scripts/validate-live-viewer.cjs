const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {loadPlaywright, browserOptions} = require('./browser-runtime.cjs');
const {chromium} = loadPlaywright();

const root = path.resolve(__dirname, '..');
const out = path.join(root, 'evidence/aws');
fs.mkdirSync(out, {recursive: true});
function fingerprint(file) {
  const bytes = fs.readFileSync(path.join(root, file));
  return {path: file, bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex')};
}
function metrics() {
  return {width: innerWidth, height: innerHeight, scrollWidth: document.documentElement.scrollWidth, scrollHeight: document.documentElement.scrollHeight};
}

(async () => {
  const browser = await chromium.launch(browserOptions());
  const receipt = {
    schema: 1, timestamp: new Date().toISOString(), browser: browser.version(),
    artifact: fingerprint('kirocrew-demo-live.html'),
    diagrams: ['kirocrew-security-layers-browser.html', 'kirocrew-ec2-live.html'].map(fingerprint),
    measurements: [], interactions: [], errors: [], screenshots: [], status: 'running',
    scope: 'New wrapper integration, embedded byte equality, reduced-frame containment and viewer interaction checks. Existing diagram geometry was not modified.',
  };
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 900}, colorScheme: 'light'});
    page.on('pageerror', e => receipt.errors.push(String(e)));
    await page.goto('file://' + path.join(root, 'kirocrew-demo-live.html'));
    assert.equal(await page.locator('#tab-ec2').getAttribute('aria-selected'), 'true');
    for (const [view, file] of [['ec2', 'kirocrew-ec2-live.html'], ['security', 'kirocrew-security-layers-browser.html']]) {
      await page.locator('#tab-' + view).click();
      const srcdoc = await page.locator('#' + view + '-frame').getAttribute('srcdoc');
      assert.deepEqual(Buffer.from(srcdoc, 'utf8'), fs.readFileSync(path.join(root, file)), view + ' byte-identical embedded document');
    }
    receipt.interactions.push('Default EC2 view and exact embedded document byte equality');
    for (const [width, height] of [[1440, 900], [1600, 1000], [1920, 1080], [2048, 1320]]) {
      await page.setViewportSize({width, height});
      for (const view of ['ec2', 'security', 'reference']) {
        await page.locator('#tab-' + view).click();
        assert.equal(await page.locator('#tab-' + view).getAttribute('aria-selected'), 'true');
        const outer = await page.evaluate(metrics);
        assert(outer.scrollWidth <= width, JSON.stringify({view, outer}));
        if (view === 'reference') {
          assert.equal(await page.locator('tbody tr').count(), 5);
          assert.equal(await page.locator('tbody .pending').count(), 1, 'Native backend remains pending in this candidate');
          receipt.measurements.push({width, height, view, outer, verticalScroll: 'intentional reference document'});
          continue;
        }
        assert(outer.scrollHeight <= height, JSON.stringify({view, outer}));
        const frame = await page.locator('#' + view + '-frame').contentFrame();
        await frame.locator('.diagram-container > svg').waitFor();
        for (const theme of ['light', 'dark']) {
          if (await frame.locator('html').getAttribute('data-theme') !== theme) await frame.locator('#btn-theme').click();
          await frame.locator('body').evaluate(async () => {
            await Archify.viewerChromeLayout.whenStable();
            await Archify.readerLayout.whenStable();
            await Archify.viewerChromeLayout.whenStable();
          });
          const inner = await frame.locator('body').evaluate(metrics);
          assert(inner.scrollWidth <= inner.width, JSON.stringify({view, theme, width, height, inner}));
          assert(inner.scrollHeight <= inner.height, JSON.stringify({view, theme, width, height, inner}));
          const svg = await frame.locator('.diagram-container > svg').evaluate(el => {
            const r = el.getBoundingClientRect();
            return {left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height};
          });
          assert(svg.left >= -1 && svg.top >= -1 && svg.right <= inner.width + 1 && svg.bottom <= inner.height + 1, JSON.stringify({view, theme, inner, svg}));
          if (view === 'security') {
            assert.equal(await frame.locator('#node-endpoint-control').count(), 1);
            const caveatBottom = await frame.locator('.browser-caveat').evaluate(el => el.getBoundingClientRect().bottom);
            assert(caveatBottom <= inner.height, JSON.stringify({view, caveatBottom, inner}));
          }
          receipt.measurements.push({width, height, view, theme, outer, inner, svg});
          if (width === 1440 || width === 2048) {
            const filename = `viewer-${view}-${width}-${theme}.png`;
            await page.screenshot({path: path.join(out, filename)});
            receipt.screenshots.push('evidence/aws/' + filename);
          }
        }
      }
    }
    await page.setViewportSize({width: 1440, height: 900});
    await page.locator('#tab-ec2').focus();
    await page.keyboard.press('ArrowRight');
    assert.equal(await page.locator('#tab-security').getAttribute('aria-selected'), 'true');
    await page.keyboard.press('End');
    assert.equal(await page.locator('#tab-reference').getAttribute('aria-selected'), 'true');
    await page.keyboard.press('Home');
    assert.equal(await page.locator('#tab-ec2').getAttribute('aria-selected'), 'true');
    await page.keyboard.press('ArrowLeft');
    assert.equal(await page.locator('#tab-reference').getAttribute('aria-selected'), 'true');
    assert.equal(await page.locator('[role=tab][tabindex="0"]').count(), 1);
    receipt.interactions.push('Roving tab focus and ArrowRight, ArrowLeft, Home and End activation');
    for (const id of ['detail-identities', 'detail-baselines']) {
      await page.locator('#' + id + ' summary').click();
      assert.equal(await page.locator('#' + id).getAttribute('open'), '');
      await page.locator('#' + id + ' summary').click();
      assert.equal(await page.locator('#' + id).getAttribute('open'), null);
    }
    await page.screenshot({path: path.join(out, 'viewer-reference.png'), fullPage: true});
    receipt.screenshots.push('evidence/aws/viewer-reference.png');
    receipt.interactions.push('Both evidence details open and close; reference screenshot includes all content');
    for (const view of ['ec2', 'security']) {
      await page.locator('#tab-' + view).click();
      const frame = await page.locator('#' + view + '-frame').contentFrame();
      await frame.locator('#btn-node-finder').click();
      await frame.locator('#node-finder-input').fill(view === 'ec2' ? 'Crew' : 'Endpoint');
      assert((await frame.locator('#node-finder-results').innerText()).trim().length > 0);
      await page.keyboard.press('Escape');
      await frame.locator(view === 'ec2' ? '#node-crew-runtime' : '#node-endpoint-control').click();
      await page.keyboard.press('Escape');
      await frame.locator('#btn-present').click();
      assert.equal(await frame.locator('html').getAttribute('data-present'), 'true');
      await page.keyboard.press('Escape');
      assert.notEqual(await frame.locator('html').getAttribute('data-present'), 'true');
      receipt.interactions.push(view + ' frame search, node focus and presentation Escape work inside wrapper');
    }
    await page.goto('file://' + path.join(root, 'kirocrew-demo-live.html') + '#reference');
    assert.equal(await page.locator('#tab-reference').getAttribute('aria-selected'), 'true');
    await page.goto('file://' + path.join(root, 'kirocrew-demo-live.html') + '#unknown');
    assert.equal(await page.locator('#tab-ec2').getAttribute('aria-selected'), 'true');
    receipt.interactions.push('Direct evidence fragment and invalid-fragment EC2 fallback');
    assert.deepEqual(receipt.errors, []);
    receipt.status = 'pass';
  } catch (e) {
    receipt.status = 'fail'; receipt.failure = String(e); process.exitCode = 1;
  } finally {
    fs.writeFileSync(path.join(out, 'viewer-browser-receipt.json'), JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify({status: receipt.status, failure: receipt.failure, measurements: receipt.measurements.length, interactions: receipt.interactions}));
    await browser.close();
  }
})();
