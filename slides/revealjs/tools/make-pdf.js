#!/usr/bin/env node
// Usage: node tools/make-pdf.js [out.pdf]     (default: pdf/slides.pdf)
// Renders index.html?print-pdf to a PDF, one page per slide (1280x720), backgrounds included.
// Needs Chrome/Chromium: CHROME_PATH or PUPPETEER_EXECUTABLE_PATH, else google-chrome(-stable)/chromium on PATH.
//
// Why not a plain `chrome --print-to-pdf`: reveal.js builds the print layout asynchronously and sets the page
// size with an @page rule; a one-shot print fires too early (blank/Letter pages). Here we wait for reveal's own
// 'pdf-ready' event, then for fonts and every <img>, and print with preferCSSPageSize + printBackground.
'use strict';
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const puppeteer = require('puppeteer-core');

const root = path.resolve(__dirname, '..');
const out = path.resolve(process.argv[2] || path.join(root, 'pdf', 'slides.pdf'));

function chromePath() {
  const env = process.env.CHROME_PATH || process.env.PUPPETEER_EXECUTABLE_PATH;
  if (env) return env;
  for (const bin of ['google-chrome-stable', 'google-chrome', 'chromium-browser', 'chromium']) {
    try { return execSync(`which ${bin}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); } catch {}
  }
  throw new Error('Chrome not found: set CHROME_PATH');
}

(async () => {
  const browser = await puppeteer.launch({ executablePath: chromePath(), headless: true,
    args: ['--no-sandbox', '--allow-file-access-from-files'] });
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 720 });
    await page.evaluateOnNewDocument(() => {
      const hook = () => {
        if (!window.Reveal || !Reveal.on) return setTimeout(hook, 20);
        Reveal.on('pdf-ready', () => { window.__pdfReady = true; });
      };
      hook();
    });
    await page.goto('file://' + path.join(root, 'index.html') + '?print-pdf', { waitUntil: 'load' });
    await page.waitForFunction(() => window.__pdfReady === true, { timeout: 60000 });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForFunction(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0),
      { timeout: 30000 }).catch(() => console.warn('warning: some images did not load'));
    await new Promise((r) => setTimeout(r, 500));
    const pages = await page.evaluate(() => document.querySelectorAll('.pdf-page').length);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    await page.pdf({ path: out, preferCSSPageSize: true, printBackground: true });
    console.log(`${out}: ${pages} pages`);
  } finally {
    await browser.close();
  }
})().catch((e) => { console.error(e); process.exit(1); });
