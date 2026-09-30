// extract_annex_tables.js
// Run in the EUR-Lex OJ HTML page (browser session) to extract all tables as
// DOM rows (innerText per cell, NBSP normalized). EUR-Lex sits behind an AWS
// WAF that blocks urllib and headless Chrome, so this runs in a real browser.
//
// Usage (in the shared browser page):
//   const result = await run_playwright_code(page, { code: fs.readFileSync('scripts/extract_annex_tables.js') })
// Returns: { tables: [ { index, rows, cols } ], url, title }
(() => {
  const tables = Array.from(document.querySelectorAll('table')).map((t, i) => {
    const rows = Array.from(t.querySelectorAll('tr')).map((tr) =>
      Array.from(tr.querySelectorAll('th, td')).map((c) =>
        (c.innerText || '').replace(/\u00a0/g, ' ').trim()
      )
    );
    return { index: i, rows, cols: rows.length ? Math.max(...rows.map((r) => r.length)) : 0 };
  });
  return {
    tables,
    url: location.href,
    title: document.title,
  };
})();