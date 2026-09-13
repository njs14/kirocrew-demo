'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {loadPlaywright, browserOptions} = require('../browser-runtime.cjs');

test('default launch uses Playwright browser discovery, without a machine-specific executable', () => {
  assert.deepEqual(browserOptions({}), {headless: true});
});
test('explicit browser executable is an existing file and is preserved', () => {
  assert.equal(browserOptions({KIRO_DEMO_BROWSER_EXECUTABLE: process.execPath}).executablePath, process.execPath);
  assert.throws(() => browserOptions({KIRO_DEMO_BROWSER_EXECUTABLE: '/definitely/missing/browser'}), /existing browser executable/);
});
test('missing module has local setup instructions and never invokes an installer', () => {
  assert.throws(() => loadPlaywright({KIRO_DEMO_PLAYWRIGHT: '/definitely/missing/module'}), /npm ci --ignore-scripts/);
});
test('an explicit module override can supply an existing runtime', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kiro-demo-module-'));
  try {
    fs.writeFileSync(path.join(dir, 'index.js'), 'module.exports = {providedRuntime: true};');
    assert.equal(loadPlaywright({KIRO_DEMO_PLAYWRIGHT: dir}).providedRuntime, true);
  } finally { fs.rmSync(dir, {recursive: true}); }
});
