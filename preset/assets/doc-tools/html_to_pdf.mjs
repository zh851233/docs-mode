// HTML → PDF（Playwright Chromium 打印）—— 配合 md_to_html.py 使用
// 用法：node html_to_pdf.mjs <input.html> <output.pdf>
// 依赖：playwright 可从当前工作目录解析（在有 node_modules/playwright 的目录下运行，
//       如项目 front 目录；或 npm i -g playwright）
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

// 从 cwd 解析 playwright（脚本可能在 preset 目录，而 playwright 在项目 node_modules）
const require = createRequire(resolve(process.cwd(), 'noop.js'));
const { chromium } = require('playwright');

const [,, htmlPath, pdfPath] = process.argv;
if (!htmlPath || !pdfPath) {
  console.error('用法：node html_to_pdf.mjs <input.html> <output.pdf>');
  process.exit(1);
}

const url = pathToFileURL(resolve(htmlPath)).href;
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
await page.pdf({
  path: pdfPath,
  format: 'A4',
  margin: { top: '18mm', bottom: '18mm', left: '16mm', right: '16mm' },
  printBackground: true,
  displayHeaderFooter: true,
  headerTemplate: '<div style="font-size:9px;color:#888;width:100%;text-align:center;padding:0 16mm;">' + 
                  '<span class="title"></span></div>',
  footerTemplate: '<div style="font-size:9px;color:#888;width:100%;text-align:center;">第 <span class="pageNumber"></span> 页 / 共 <span class="totalPages"></span> 页</div>',
});
await browser.close();
console.log('OK:', pdfPath);
