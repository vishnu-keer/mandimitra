// Usage: node html_to_pdf.js in.html out.pdf [landscape]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [inp, out, orient] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + path.resolve(inp), { waitUntil: 'networkidle' });
  await p.pdf({ path: out, format: 'A4', landscape: orient === 'landscape', printBackground: true,
                preferCSSPageSize: true, displayHeaderFooter: orient !== 'landscape' && orient !== 'poster',
                headerTemplate: '<span></span>',
                footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#5b6472"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
                margin: orient === 'poster' ? undefined : { top: '18mm', bottom: '18mm', left: '16mm', right: '16mm' } });
  await b.close();
})().catch(e => { console.error(e); process.exit(1); });
