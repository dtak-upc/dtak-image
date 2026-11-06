#!/usr/bin/env node
// Usage: node tools/serve.js [--port N] [--host H]   (or `npm start`)
// Local web server with live reload for the DTAK slides:
// serves the folder, / is index.html, reloads on changes to index.html or theme/
// (hash: true in deck.js, so the reload stays on the current slide).
//
// Why not reveal.js's own `npm start`: that's the gulp dev server of the reveal.js repo
// itself; here reveal.js is just a dependency in node_modules, so there is no such script.
// Zero dependencies (Node >= 20 for recursive fs.watch on Linux), so it also runs after
// `npm prune --omit=dev`.
'use strict';
const fs = require('fs');
const http = require('http');
const path = require('path');

const root = path.resolve(__dirname, '..');
const args = process.argv.slice(2);
const opt = (name, def) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : def; };
const port = Number(opt('--port', process.env.PORT || 8000));
const host = opt('--host', process.env.HOST || 'localhost');

const types = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp',
  '.woff': 'font/woff', '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.pdf': 'application/pdf',
  '.mp4': 'video/mp4', '.webm': 'video/webm',
};

const reloadSnippet = `<script>
new EventSource('/__reload').addEventListener('reload', () => location.reload());
</script>`;

// --- live reload: Server-Sent Events, one 'reload' event per (debounced) change ---
const clients = new Set();
let timer;
function onChange(dir, file) {
  if (!file || /(^|\/)(_review\.html|\..*\.swp|.*~|\.#.*)$/.test(file)) return;
  clearTimeout(timer);
  timer = setTimeout(() => {
    console.log(`changed: ${dir}/${file} -> reloading ${clients.size} client(s)`);
    for (const res of clients) res.write('event: reload\ndata: \n\n');
  }, 100);
}
for (const dir of ['theme']) {
  fs.watch(path.join(root, dir), { recursive: true }, (_ev, file) => onChange(dir, file));
}
fs.watch(root, (_ev, file) => { if (file === 'index.html') onChange('.', file); });

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x');
  if (url.pathname === '/__reload') {
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' });
    res.write('\n');
    clients.add(res);
    req.on('close', () => clients.delete(res));
    return;
  }

  let file = path.join(root, decodeURIComponent(url.pathname));
  if (!file.startsWith(root + path.sep)) { res.writeHead(403); return res.end('Forbidden'); }
  fs.stat(file, (err, st) => {
    if (!err && st.isDirectory()) {
      if (!url.pathname.endsWith('/')) {  // so relative paths (img/, ../../theme) resolve
        res.writeHead(301, { Location: url.pathname + '/' + url.search });
        return res.end();
      }
      file = path.join(file, 'index.html');
    }
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); return res.end('Not found'); }
      const ext = path.extname(file).toLowerCase();
      res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream',
                           'Cache-Control': 'no-store' });
      if (ext === '.html') {
        const html = data.toString();
        const i = html.lastIndexOf('</body>');
        return res.end(i >= 0 ? html.slice(0, i) + reloadSnippet + html.slice(i) : html + reloadSnippet);
      }
      res.end(data);
    });
  });
}).listen(port, host, () => {
  console.log(`Serving ${root} at http://${host}:${port}/ (live reload on index.html, theme/; Ctrl+C to stop)`);
});
