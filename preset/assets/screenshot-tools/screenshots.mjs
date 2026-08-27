// 通用界面截图工具 screenshots.mjs —— 使用说明书第四章「系统功能界面设计」配图用。
// 用法：
//   1. 编辑下方 CONFIG（URL、截图清单、等待条件）
//   2. node screenshots.mjs [--server-command "npm run dev"] [--server-dir <目录>]
//   3. 截出的图在 OUT_DIR，每张图自动生成 <名>.ocr.txt（用 OCR 验证内容，防止 loading/空白图入库）
//
// 清单条目字段：
//   name    输出文件名（不含扩展名）
//   wait    (ms) 打开页面后等待（默认 6000）
//   click   可选：CSS 选择器数组，逐个 evaluate 点击（间隔 waitAfterClick ms）
//   fill    可选：[selector, text] 输入框填充
//   key     可选：键盘按键（如 'Escape'）
//   shot    可选：'element:<sel>' 只截某元素
//   ready   可选：JS 表达式（页面 evaluate），为 true 才截图（轮询等待，默认 120s 超时）
//   ocr     可选：false 跳过 OCR（默认对每张图调 OCR 验证，需要 qwen OCR 工具时在会话中执行）

const CONFIG = {
  baseUrl: 'http://localhost:3000/',
  outDir: './screenshots',
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
  shots: [
    // 示例：
    // { name: '01-主界面', wait: 15000, ready: "!document.body.innerText.includes('正在装载')" },
    // { name: '02-分析结果', wait: 15000, click: ['#map-canvas'], waitAfterClick: 12000 },
    // { name: '03-搜索候选', fill: ['.search-input', '市民中心'], waitAfterClick: 1500 },
  ],
};

import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

// 从 cwd 解析 playwright（在有 node_modules/playwright 的目录下运行，如项目 front 目录）
const require = createRequire(resolve(process.cwd(), 'noop.js'));
const { chromium } = require('playwright');

const args = process.argv.slice(2);
const serverCmd = args.find((a, i) => a === '--server-command' && args[i + 1]) ? args[args.indexOf('--server-command') + 1] : null;
const serverDir = args.find((a, i) => a === '--server-dir' && args[i + 1]) ? args[args.indexOf('--server-dir') + 1] : null;

let serverProc = null;
async function startServer() {
  if (!serverCmd) return;
  console.log(`启动: ${serverCmd} (${serverDir || '.'})`);
  serverProc = spawn(serverCmd, { shell: true, cwd: serverDir || process.cwd(), stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 15000));
  // 轮询等待端口就绪
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch(CONFIG.baseUrl, { signal: AbortSignal.timeout(3000) });
      if (res.ok || res.status < 500) { console.log('服务就绪'); return; }
    } catch {}
    await new Promise(r => setTimeout(r, 2000));
  }
  console.log('⚠️ 服务未就绪，继续尝试截图');
}

async function waitReady(page, expr, timeoutMs = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      if (await page.evaluate(expr)) return true;
    } catch {}
    await new Promise(r => setTimeout(r, 1500));
  }
  console.log('⚠️ ready 条件超时');
  return false;
}

async function runShot(page, shot) {
  const { name, wait = 6000, click = [], fill = null, key = null, ready = null, shot: shotSel = null } = shot;
  const waitAfterClick = shot.waitAfterClick ?? 2000;
  console.log(`→ ${name}`);
  if (ready) await waitReady(page, ready);
  else await page.waitForTimeout(wait);
  if (fill) {
    await page.fill(fill[0], fill[1]);
    await page.waitForTimeout(1500);
  }
  for (const sel of click) {
    const ok = await page.evaluate((s) => {
      const el = document.querySelector(s);
      if (!el) return false;
      el.click(); return true;
    }, sel);
    console.log(`  click ${sel}: ${ok}`);
    await page.waitForTimeout(waitAfterClick);
  }
  if (key) { await page.keyboard.press(key); await page.waitForTimeout(800); }
  const outPath = join(CONFIG.outDir, `${name}.png`);
  if (shotSel && shotSel.startsWith('element:')) {
    const el = page.locator(shotSel.slice(8));
    if (await el.count()) await el.screenshot({ path: outPath });
    else { console.log(`  ⚠️ 元素不存在 ${shotSel}`); return; }
  } else {
    await page.screenshot({ path: outPath });
  }
  console.log(`  ✅ ${outPath}`);
  if (shot.ocr !== false) {
    // 留一个占位：OCR 文本文件由会话中模型调用 qwen OCR 后写入
    writeFileSync(join(CONFIG.outDir, `${name}.ocr.txt`), '', 'utf-8');
  }
}

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: CONFIG.viewport, deviceScaleFactor: CONFIG.deviceScaleFactor });
mkdirSync(resolve(CONFIG.outDir), { recursive: true });
await startServer();
await page.goto(CONFIG.baseUrl, { waitUntil: 'domcontentloaded', timeout: 90000 });
for (const shot of CONFIG.shots) {
  try { await runShot(page, shot); } catch (e) { console.log(`  ❌ ${shot.name}: ${e.message}`); }
}
await browser.close();
if (serverProc) serverProc.kill();
console.log('全部完成。OCR 验证步骤：对每张 <name>.png 调用 mcp__qwen-mm-plugins-api__ocr 核实内容后，把结果写入 <name>.ocr.txt（模型在会话中执行）。');
