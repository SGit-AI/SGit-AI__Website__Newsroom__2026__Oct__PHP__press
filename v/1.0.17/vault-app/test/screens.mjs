// Render every view of the built app, with a stand-in for the vault bridge, at desktop and phone widths.
//   node vault-app/test/screens.mjs <vault clone> <out dir> [--no-bridge]
// Serves the clone over a local HTTP port; window.sg.vfs.* reads from it, the way the bridge reads from the vault.
// Fails (exit 1) on any page error or console error.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require('/opt/node-tools/node_modules/playwright')); }

const [vault, out] = process.argv.slice(2);
const bridge = !process.argv.includes('--no-bridge');
fs.mkdirSync(out, { recursive: true });
const root = path.resolve(vault);

const server = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split('?')[0]);
  if (url === '/__list') {
    const prefix = new URL(req.url, 'http://x').searchParams.get('p') || '';
    const dir = path.join(root, prefix);
    const rows = fs.existsSync(dir) ? fs.readdirSync(dir, { withFileTypes: true }).filter(d => d.isFile()).map(d => ({ path: prefix + '/' + d.name, name: d.name, size: fs.statSync(path.join(dir, d.name)).size, type: 'file' })) : [];
    res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify(rows)); return;
  }
  const p = path.join(root, url);
  if (!p.startsWith(root) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end('nope'); return; }
  const type = { '.html': 'text/html', '.json': 'application/json', '.webp': 'image/webp', '.png': 'image/png' }[path.extname(p)] || 'text/plain';
  res.writeHead(200, { 'content-type': type + '; charset=utf-8' }); fs.createReadStream(p).pipe(res);
});
await new Promise(r => server.listen(0, r));
const base = 'http://127.0.0.1:' + server.address().port;

const shim = `(() => {
  const B = ${JSON.stringify(base)};
  const get = async p => { const r = await fetch(B + '/' + p.replace(/^\\/+/, '')); if (!r.ok) throw new Error('No such file: ' + p); return r; };
  const st = {};
  window.__previews = [];
  window.sg = {
    vfs: { readText: async p => (await get(p)).text(), read: async p => (await get(p)).arrayBuffer(),
           list: async p => (await fetch(B + '/__list?p=' + encodeURIComponent(p))).json() },
    state: { get: async k => st[k] ?? null, set: async (k, v) => { st[k] = v; return { ok: true }; } },
    ui: { preview: async p => { window.__previews.push(p); return { ok: true, path: p }; }, message: (t) => console.log('[toast] ' + t) },
    app: { context: 'app', writable: false, vaultName: 'test', vaultId: 'test' },
  };
})();`;

const errors = [];
const browser = await chromium.launch({ executablePath: fs.existsSync('/opt/pw-browsers/chromium') ? undefined : undefined });
async function run(label, viewport, scheme) {
  const ctx = await browser.newContext({ viewport, colorScheme: scheme, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on('pageerror', e => errors.push(`${label}: pageerror ${e.message}`));
  page.on('console', m => { if (m.type() === 'error') errors.push(`${label}: console ${m.text()}`); });
  if (bridge) await page.addInitScript(shim);
  await page.goto(base + '/index.html');
  await page.waitForSelector('.tile');
  await page.waitForTimeout(800);
  const shot = async name => { await page.waitForTimeout(450); await page.screenshot({ path: path.join(out, `${label}-${name}.png`) }); };
  const mode = await page.textContent('#modeT');
  console.log(label, 'mode:', mode);
  await shot('overview');
  for (const v of ['sources', 'wall', 'claims', 'timeline', 'desk', 'about']) {
    await page.click(`.side [data-go="${v}"]`);
    await shot(v);
  }
  await page.click('.side [data-go="sources"]');
  await page.click('[data-layout="table"]'); await shot('sources-table');
  await page.click('[data-layout="cards"]');
  await page.fill('#fq', 'ncsc'); await shot('sources-filtered');
  await page.click('.card');
  await page.waitForSelector('#dnotes p, #dnotes h1, #dnotes h2, #dnotes li', { timeout: 5000 }).catch(() => errors.push(label + ': notes did not render'));
  await shot('drawer');
  await page.click('.drawer .capc').catch(() => {});
  await page.waitForSelector('#lb.on img', { timeout: 5000 }).catch(() => errors.push(label + ': viewer did not open'));
  await page.waitForTimeout(800); await shot('viewer');
  await page.keyboard.press('ArrowRight'); await shot('viewer-next');
  await page.keyboard.press('Escape'); await page.keyboard.press('Escape');
  await page.click('.side [data-go="overview"]');
  await page.fill('#q', 'wiz 70'); await shot('search');
  await page.keyboard.press('Enter'); await shot('search-picked');
  await page.keyboard.press('Escape');
  await page.click('.side [data-go="overview"]');
  await page.click('.legend button >> nth=0'); await shot('claims-from-legend');
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (overflow > 0) errors.push(`${label}: horizontal overflow ${overflow}px`);
  if (bridge) console.log(label, 'previews:', await page.evaluate(() => window.__previews));
  await ctx.close();
}
await run('desktop-light', { width: 1440, height: 900 }, 'light');
await run('desktop-dark', { width: 1440, height: 900 }, 'dark');
await run('phone', { width: 390, height: 844 }, 'light');
await browser.close(); server.close();
if (errors.length) { console.error(errors.join('\n')); process.exit(1); }
console.log('ok: no page or console errors');
