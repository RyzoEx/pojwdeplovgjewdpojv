// Renders preview frames with headless Chrome: node preview/capture.mjs <outDir>
// Needs: npm i puppeteer-core (any dir on NODE_PATH), a static server on :8765 serving the repo root.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const out = process.argv[2] || 'build/preview';
fs.mkdirSync(out, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: process.env.CHROME || '/usr/local/bin/google-chrome',
  args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
const page = await browser.newPage();
page.on('console', m => console.log('[page]', m.text()));
page.on('pageerror', e => console.log('[pageerror]', e.message));

async function open(query, w = 900, h = 900) {
  await page.setViewport({ width: w, height: h });
  await page.goto(`http://localhost:8765/preview/index.html?capture&${query}`, { waitUntil: 'networkidle0' });
  await page.waitForFunction('window.__ready === true', { timeout: 60000 });
}

const shots = JSON.parse(process.argv[3] || '[]');
for (const s of shots) {
  await open(s.query, s.w, s.h);
  if (s.frames) {
    for (let i = 0; i < s.frames; i++) {
      const t = (s.t0 || 0) + i * (s.dt || 0.05);
      await page.evaluate((t, y) => window.renderAt(t, y), t, s.yaw0 !== undefined ? s.yaw0 + i * (s.dyaw || 0) : undefined);
      await page.screenshot({ path: `${out}/${s.name}_${String(i).padStart(3, '0')}.png` });
    }
  } else {
    await page.evaluate((t) => window.renderAt(t), s.t || 0);
    await page.screenshot({ path: `${out}/${s.name}.png` });
  }
  console.log('captured', s.name);
}
await browser.close();
