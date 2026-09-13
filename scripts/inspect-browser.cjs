const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'evidence/browser');
fs.mkdirSync(out, {recursive: true});
const {loadPlaywright, browserOptions} = require('./browser-runtime.cjs');
const {chromium} = loadPlaywright();
(async()=>{const b=await chromium.launch(browserOptions());try{const p=await b.newPage({viewport:{width:1440,height:900}});await p.goto(process.env.KIRO_DEMO_VIEWER_URL || pathToFileURL(path.join(root, 'kirocrew-aws-remote.html')).href);const frame=await p.locator('#security-frame').contentFrame();await frame.locator('.diagram-container > svg').waitFor();await frame.getByRole('button',{name:'Find a node',exact:true}).click();console.log('INPUTS',await frame.locator('input').evaluateAll(es=>es.map(e=>({id:e.id,placeholder:e.placeholder,role:e.getAttribute('role')}))));await p.keyboard.press('Escape');await frame.locator('#node-endpoint-control').click();console.log('FOCUS',await frame.locator('html').evaluate(e=>e.outerHTML.slice(0,1000)));console.log('VISIBLE DIALOG',await frame.locator('[role=dialog]').evaluateAll(es=>es.filter(e=>e.getBoundingClientRect().height).map(e=>({label:e.getAttribute('aria-label'),id:e.id,text:e.textContent.slice(0,400)}))));await p.screenshot({path:path.join(out, 'endpoint-focused-initial.png')});}finally{await b.close()}})();
