'use strict';

const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

function loadPlaywright(env = process.env) {
  // Default to this checkout's npm ci installation. Overrides are explicit,
  // local module locations; this helper never installs or downloads a browser.
  const modulePath = env.KIRO_DEMO_PLAYWRIGHT
    ? path.resolve(env.KIRO_DEMO_PLAYWRIGHT)
    : path.join(root, 'node_modules', 'playwright');
  try {
    return require(modulePath);
  } catch (error) {
    throw new Error(`Cannot load Playwright from ${modulePath}. Run npm ci --ignore-scripts in the checkout, or set KIRO_DEMO_PLAYWRIGHT to an existing Playwright module directory.`, {cause: error});
  }
}

function browserOptions(env = process.env) {
  const options = {headless: true};
  if (env.KIRO_DEMO_BROWSER_EXECUTABLE) {
    const executablePath = path.resolve(env.KIRO_DEMO_BROWSER_EXECUTABLE);
    if (!fs.statSync(executablePath, {throwIfNoEntry: false})?.isFile()) {
      throw new Error('KIRO_DEMO_BROWSER_EXECUTABLE must point to an existing browser executable.');
    }
    options.executablePath = executablePath;
  }
  return options;
}

module.exports = {loadPlaywright, browserOptions};
