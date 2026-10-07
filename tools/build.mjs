#!/usr/bin/env node
/**
 * 由 preset/（单一真源）生成 docs-mode bundle 的包根产物：
 *   cordis.patch.yml   insert 一条 @deepseek-ai/dsh-agent-preset 声明
 *   skills/            随包技能
 *   assets/            随包资产（模板与工具脚本）
 *
 * 为什么是「声明式 bundle」而不是 1.x 的安装器：
 *   dsh 0.2 起不再读取 $DSH_HOME/.agent-presets/<id>/。
 *   见 @deepseek-ai/dsh-agent-preset 的
 *   skills/editing-cordis-compositions/SKILL.md「Migrate a legacy preset」。
 *
 * 技能/资产路径怎么跨机器成立：
 *   原写法 new URL('skills/', baseUrl) 依赖 preset 目录变量 baseUrl，
 *   而 bundle 格式下它在不在、指向哪，都无法离线证实；一旦未定义，
 *   skill-filesystem 会求值失败 → 整个 preset 挂载失败。
 *   因此改为「从 DSH profile 清单解析本包安装目录」——这正是
 *   dsh-plugin-manager 的既有回退写法（pathToFileURL(join(profileDir,'package.json'))）。
 *   bundle 装在 profile 的 node_modules 里，所以必然可解析，且跨机器成立。
 *
 * 用法：node tools/build.mjs
 */
import { readFileSync, writeFileSync, existsSync, cpSync, rmSync, readdirSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO = dirname(dirname(fileURLToPath(import.meta.url)))

// 包名以自身 package.json 为准，避免改名后漏改 patch
const pkg = JSON.parse(readFileSync(join(REPO, 'package.json'), 'utf8'))
const PKG_NAME = pkg.name
if (!PKG_NAME) { console.error('X package.json 缺少 name'); process.exit(1) }

const SRC = join(REPO, 'preset')
if (!existsSync(SRC)) { console.error('X 找不到 preset/ 目录: ' + SRC); process.exit(1) }

const presetYml = readFileSync(join(SRC, 'preset.yml'), 'utf8')
const agentYml = readFileSync(join(SRC, 'agent.cordis.yml'), 'utf8')

function field(text, key) {
  const m = new RegExp(`^${key}:[ \\t]*(.*)$`, 'm').exec(text)
  return m ? m[1].trim() : undefined
}
const id = 'docs'
const name = field(presetYml, 'name') ?? '文书模式'
const description = field(presetYml, 'description') ?? ''

/**
 * 生成「解析本包安装目录并拼上子路径」的 !!js 表达式。
 * 返回 `(<IIFE>)('<sub>')` —— IIFE 内已 join 到子目录。
 * 不能写成 `${R},'assets'`：那是逗号运算符，只会得到 'assets'。
 */
const resolverFor = (sub) =>
  `(()=>{const c=process.getBuiltinModule('node:module').createRequire(` +
  `process.getBuiltinModule('node:url').pathToFileURL(` +
  `process.getBuiltinModule('node:path').join(` +
  `process.getBuiltinModule('node:os').homedir(),'.dsh','profiles','desktop','package.json')).href);` +
  `return process.getBuiltinModule('node:path').join(` +
  `process.getBuiltinModule('node:path').dirname(c.resolve('${PKG_NAME}/package.json')),'${sub}')})()`

// ── 改写 1：customSkillDirs 指向随包 skills/ ────────────────────────────────
const OLD_SKILLS = "process.getBuiltinModule('node:url').fileURLToPath(new URL('skills/', baseUrl))"
if (!agentYml.includes(OLD_SKILLS)) {
  console.error('X 未在 preset/agent.cordis.yml 中找到预期的 customSkillDirs 表达式：')
  console.error('  ' + OLD_SKILLS)
  process.exit(1)
}
let body = agentYml.replace(OLD_SKILLS, resolverFor('skills'))

// 同步更新可能残留的旧版注释
body = body.replace(
  /# 随 preset 打包的技能（doc-template-learning、tech-doc-deai）位于本目录的\n(\s*)# skills\/ 下，通过 customSkillDirs 注册；`baseUrl` 是 preset 自己的目录，\n\s*# 所以整个目录拷贝\/压缩到任何机器的 ~\/\.dsh\/\.agent-presets\/ 下，技能随包生效。/,
  `# 随包携带的技能位于包内 skills/ 下，通过 customSkillDirs 注册。路径写法是\n$1# 「从 DSH profile 清单解析本包安装目录」——bundle 装在 profile 的 node_modules\n$1# 里，因此跨机器、跨 DSH_HOME 均成立。`,
)

// ── 改写 1b：persona suffix 告知资产位置 ────────────────────────────────────
const SUFFIX_ANCHOR = '    suffix: 工作目录：{{cwd}}。'
const SUFFIX_NEW = `    suffix: |-
      工作目录：{{cwd}}。
      本模式的模板库与工具脚本随包提供，位于：${resolverFor('assets')}
      其中 templates/ 为 11 类内置模板（<类别>-骨架.md 与 <类别>-风格卡.md），
      doc-tools/ 为质量保障脚本，docx-tools/ 为 Markdown⇄Word 转换与校验，
      screenshot-tools/ 为界面截图自动化。需要时用 read/glob 读取，先看各自 README。`
if (body.includes(SUFFIX_ANCHOR)) body = body.replace(SUFFIX_ANCHOR, SUFFIX_NEW)
else console.warn('  ! persona suffix 锚点未命中，跳过资产路径注入')

// ── 改写 2：移除 dsh 0.2 已不存在的插件行 ──────────────────────────────────
// dsh-workflow-worker-thread 在 0.2.0-rc2 中已无此包；文书模式本就禁用 workflow。
const kept = []
let skipping = false
for (const line of body.split('\n')) {
  if (/^- id: workflow-worker-thread\s*$/.test(line)) { skipping = true; continue }
  if (skipping) {
    if (/^- id: /.test(line)) skipping = false
    else continue
  }
  kept.push(line)
}
body = kept.join('\n')

// ── 缩进到 config.plugins 之下（10 格） ────────────────────────────────────
// 只裁尾空白并整体加 10 格：保留行首相对缩进，否则 `name:` 会掉到第 1 列。
const INDENT = ' '.repeat(10)
const pluginsBlock = body
  .split('\n')
  .map(l => (l.trim() === '' ? '' : INDENT + l.replace(/\s+$/, '')))
  .join('\n')
  .replace(/\s+$/, '')

const header = `# docs-mode bundle —— 文书模式（技术文档撰写专员）
#
# 本文件由 tools/build.mjs 从 preset/ 生成，请勿手工编辑：
# 改动模式定义请编辑 preset/agent.cordis.yml，改动元数据请编辑 preset/preset.yml。
#
# 自包含 preset bundle：安装后由 @deepseek-ai/dsh-agent-preset 直接声明，
# 不再向 $DSH_HOME/.agent-presets/ 拷贝目录（该格式自 dsh 0.2 起已废弃）。
#
# 随包资产：
#   skills/  doc-template-learning / tech-doc-deai / doc-quality
#   assets/  doc-tools / docx-tools / screenshot-tools / templates(11 类)
#
# 技能与资产路径通过「从 DSH profile 清单解析本包」得到，跨机器、跨 DSH_HOME 均成立。
`

const patch = `${header}- insert:
    - id: preset-docs
      name: '@deepseek-ai/dsh-agent-preset'
      config:
        id: ${id}
        name: ${JSON.stringify(name)}
        description: ${JSON.stringify(description)}
        plugins:
${pluginsBlock}
`

// ── 铺 skills/ 与 assets/ ──────────────────────────────────────────────────
for (const d of ['skills', 'assets']) {
  const dest = join(REPO, d)
  if (existsSync(dest)) rmSync(dest, { recursive: true, force: true })
  cpSync(join(SRC, d), dest, { recursive: true })
  const n = countFiles(dest)
  console.log(`  · ${d}/  (${n} 个文件)`)
}
writeFileSync(join(REPO, 'cordis.patch.yml'), patch, 'utf8')
console.log('  · cordis.patch.yml  (UTF-8 无 BOM)')

// ── 生成即自检 ─────────────────────────────────────────────────────────────
function countFiles(dir) {
  let n = 0
  for (const e of readdirSync(dir)) {
    const p = join(dir, e)
    n += statSync(p).isDirectory() ? countFiles(p) : 1
  }
  return n
}

const problems = []
if (!patch.includes(`c.resolve('${PKG_NAME}/package.json')`)) problems.push('patch 未解析本包名')
if (!/\),'skills'\)/.test(patch)) problems.push('skills 解析表达式缺失')
if (!/\),'assets'\)/.test(patch)) problems.push('assets 解析表达式缺失')
if (!/^- insert:/m.test(patch)) problems.push('缺少顶层 insert')
if (!patch.includes('id: preset-docs')) problems.push('缺少 preset-docs 声明')
if (!patch.includes(`id: ${id}`)) problems.push('config.id 缺失')
if (/\$\{[^}]*\},'assets'/.test(patch)) problems.push('存在逗号运算符误用')
const pluginRows = [...patch.matchAll(/^\s{10}- id: /gm)].length
if (pluginRows < 10) problems.push(`插件条目过少(${pluginRows})`)

console.log('\n=== 自检 ===')
console.log(`  声明 id=preset-docs   config.id=${id}   name=${name}`)
console.log(`  顶层插件条目=${pluginRows}`)
console.log(`  patch 字节数=${Buffer.byteLength(patch, 'utf8')}`)
if (problems.length) {
  console.error('  ❌ ' + problems.join('; '))
  process.exit(1)
}
console.log('  ✅ 结构自检通过')
