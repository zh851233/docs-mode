#!/usr/bin/env node
/**
 * docs-mode 安装诊断 doctor.mjs —— 一条命令查清「为什么模式不出现」。
 *
 * 用法：
 *   node tools/doctor.mjs                 # 检查默认 profile（desktop）
 *   node tools/doctor.mjs --profile web   # 检查指定 profile
 *   node tools/doctor.mjs --source D:/work/docs-mode   # 同时对比源目录与已安装副本
 *
 * 检查项（覆盖本插件踩过的全部坑）：
 *   1. package.json 无 BOM、有 main、有 exports（BOM 会让 bundle 被静默跳过）
 *   2. cordis.patch.yml 存在、无 BOM、含 preset-docs 声明
 *   3. patch 里的 {{变量}} 只允许 provider / model（0.2.1-rc.3 只注册这两个）
 *   4. preset/ 与 skills/ assets/ 存在
 *   5. file: 安装时，源目录与 node_modules 副本版本是否一致（不同步 = 改完不生效）
 *   6. patch 是否声明了 preset-docs（声明式；旧版目录扫描已废弃）
 */
import { readFileSync, existsSync, readdirSync } from 'node:fs'
import { join, dirname, resolve } from 'node:path'
import { homedir } from 'node:os'

const args = process.argv.slice(2)
function arg(name, def) {
  const i = args.indexOf(name)
  return i >= 0 && args[i + 1] ? args[i + 1] : def
}

const PROFILE = arg('--profile', 'desktop')
const SOURCE = arg('--source', null)
const DSH_HOME = process.env.DSH_HOME || join(homedir(), '.dsh')
const PROFILE_DIR = join(DSH_HOME, 'profiles', PROFILE)
const INSTALLED = join(PROFILE_DIR, 'node_modules', 'dsh-docs-mode')
const PKG = 'dsh-docs-mode'

let problems = []
let warnings = []
let ok = []
function pass(msg) { ok.push(msg); console.log('  ✅ ' + msg) }
function warn(msg) { warnings.push(msg); console.log('  ⚠️  ' + msg) }
function fail(msg) { problems.push(msg); console.log('  ❌ ' + msg) }

function readJsonNoBom(path) {
  const buf = readFileSync(path)
  const hasBom = buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf
  return { json: JSON.parse(buf.toString('utf8').replace(/^\uFEFF/, '')), hasBom }
}

console.log(`\n=== docs-mode doctor ===`)
console.log(`profile: ${PROFILE}  |  DSH_HOME: ${DSH_HOME}\n`)

// 1. 安装完整性
console.log('▶ 安装完整性')
if (!existsSync(INSTALLED)) {
  fail(`${PKG} 未安装到 profile（${INSTALLED} 不存在）`)
} else {
  const pkgPath = join(INSTALLED, 'package.json')
  if (!existsSync(pkgPath)) {
    fail('package.json 缺失')
  } else {
    try {
      const { json, hasBom } = readJsonNoBom(pkgPath)
      if (hasBom) fail('package.json 有 UTF-8 BOM（会导致 bundle 被静默跳过）')
      else pass(`package.json 可解析，version=${json.version}`)
      if (json.main) pass(`main = ${json.main}`)
      else fail('package.json 缺 main（node 按包名解析会找包根 index.js）')
      if (existsSync(join(INSTALLED, json.main || ''))) pass('入口文件存在')
      else fail(`入口文件不存在：${json.main}`)
    } catch (e) {
      fail('package.json 解析失败：' + e.message)
    }
  }
}

// 2. patch 内容
console.log('\n▶ cordis.patch.yml')
const patchPath = join(INSTALLED, 'cordis.patch.yml')
if (!existsSync(patchPath)) {
  fail('cordis.patch.yml 缺失')
} else {
  const buf = readFileSync(patchPath)
  const hasBom = buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf
  const text = buf.toString('utf8').replace(/^\uFEFF/, '')
  if (hasBom) fail('cordis.patch.yml 有 BOM')
  if (!text.includes('preset-docs')) fail('patch 未声明 preset-docs（模式不会出现）')
  else pass('声明了 preset-docs')
  if (!text.includes('@deepseek-ai/dsh-agent-preset')) fail('patch 未引用 @deepseek-ai/dsh-agent-preset')
  else pass('引用 @deepseek-ai/dsh-agent-preset')
  // prompt 变量白名单（只看非注释行：注释里的占位符不参与渲染）
  const codeLines = text.split('\n').filter((l) => !/^\s*#/.test(l))
  const vars = [...codeLines.join('\n').matchAll(/\{\{([a-zA-Z_][\w.]*)\}\}/g)].map((m) => m[1])
  const allowed = new Set(['provider', 'model'])
  const bad = [...new Set(vars)].filter(v => !allowed.has(v))
  if (bad.length) fail(`patch 含非白名单 prompt 变量：${bad.join(', ')}（0.2.1-rc.3 只注册 provider/model）`)
  else pass(vars.length ? `prompt 变量合法：${[...new Set(vars)].join(', ')}` : '无 prompt 变量')
  // preset 目录
  for (const d of ['preset', 'skills', 'assets']) {
    if (existsSync(join(INSTALLED, d))) pass(`${d}/ 存在`)
    else warn(`${d}/ 缺失（部分功能不可用）`)
  }
}

// 3. file: 安装的同步检查
console.log('\n▶ 源目录与副本同步')
const profilePkg = join(PROFILE_DIR, 'package.json')
if (existsSync(profilePkg)) {
  try {
    const { json } = readJsonNoBom(profilePkg)
    const dep = (json.dependencies || {})[PKG]
    if (dep && dep.startsWith('file:')) {
      const srcDir = resolve(dirname(profilePkg), dep.slice('file:'.length))
      if (!existsSync(join(srcDir, 'package.json'))) {
        warn(`file: 源目录不存在：${srcDir}`)
      } else {
        const srcPkg = readJsonNoBom(join(srcDir, 'package.json')).json
        const instPkg = existsSync(join(INSTALLED, 'package.json'))
          ? readJsonNoBom(join(INSTALLED, 'package.json')).json : {}
        if (srcPkg.version === instPkg.version) {
          pass(`源目录与副本版本一致（${srcPkg.version}）`)
        } else {
          fail(`版本不同步：源=${srcPkg.version} 副本=${instPkg.version}（file: 安装不会自动更新，需重新安装或覆盖 node_modules）`)
        }
        // 对比 patch 是否一致
        const srcPatch = join(srcDir, 'cordis.patch.yml')
        const instPatch = join(INSTALLED, 'cordis.patch.yml')
        if (existsSync(srcPatch) && existsSync(instPatch)) {
          if (readFileSync(srcPatch, 'utf8') === readFileSync(instPatch, 'utf8')) pass('源与副本的 cordis.patch.yml 一致')
          else warn('源与副本的 cordis.patch.yml 不一致（副本可能是旧版）')
        }
      }
    } else if (dep) {
      pass(`安装方式：${dep}（非 file:，更新需重装）`)
    } else {
      warn('profile 的 dependencies 中没有 dsh-docs-mode（但 node_modules 里存在，可能是手动放置）')
    }
  } catch (e) {
    warn('读取 profile package.json 失败：' + e.message)
  }
}

// 4. DSH 版本参考
console.log('\n▶ 运行环境')
try {
  const agentPresets = join(PROFILE_DIR, 'node_modules', '@deepseek-ai', 'dsh-agent-presets', 'package.json')
  const dshPkg = join(PROFILE_DIR, 'node_modules', '@deepseek-ai', 'dsh', 'package.json')
  if (existsSync(dshPkg)) {
    const v = readJsonNoBom(dshPkg).json.version
    pass(`dsh 运行时 ${v}（本插件按 0.2.x 声明式机制适配）`)
  } else {
    warn('未找到 dsh 运行时包（asar 内置），跳过版本检查')
  }
} catch (e) { warn('版本检查失败：' + e.message) }

// 汇总
console.log('\n=== 结论 ===')
if (problems.length === 0 && warnings.length === 0) {
  console.log('  ✅ 全部检查通过。若模式仍不出现，请用 profile 副本跑 --dump-config 看 preset-docs 是否组合。')
} else if (problems.length) {
  console.log(`  ❌ ${problems.length} 个问题需要修复：`)
  problems.forEach(p => console.log('     - ' + p))
} else {
  console.log(`  ⚠️ ${warnings.length} 个警告（不致命）`)
}
process.exit(problems.length ? 1 : 0)
