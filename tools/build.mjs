#!/usr/bin/env node
/**
 * 生成 docs-mode bundle 的 cordis.patch.yml。
 *
 * preset/ 是单一真源（agent.cordis.yml + preset.yml + skills/ + assets/）。
 * 本脚本只做两件事：
 *   1. 生成 cordis.patch.yml —— insert 一条安装器声明（lib/index.js）。
 *      安装器在 DSH 启动时把 preset/ 部署到 $DSH_HOME/.agent-presets/docs/，
 *      roster 的下一次扫描就能发现「文书模式」。
 *   2. 结构自检 —— preset 关键文件与占位符是否完整。
 *
 * 为什么 patch 里不再嵌入 agent.cordis.yml 的插件行（v2.0.0 的做法）：
 *   @deepseek-ai/dsh-agent-presets 是进程级 roster 服务，config 只接受
 *   default / roots / includeShippedRoot / includeUserRoot；把单个 preset 的
 *   id/name/plugins 塞进去既不是它的 schema，也会与 host 同名服务相撞。
 *
 * 技能路径：preset/agent.cordis.yml 里 skill-filesystem 的 customSkillDirs 写
 *   '{{PRESET_DIR}}/skills'，由安装器部署时替换为真实绝对路径——不用 !!js/baseUrl，
 *   老版本 loader 也能挂载。
 *
 * 用法：node tools/build.mjs
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const REPO = dirname(dirname(fileURLToPath(import.meta.url)))
const SRC = join(REPO, 'preset')

const pkg = JSON.parse(readFileSync(join(REPO, 'package.json'), 'utf8'))
const PKG_NAME = pkg.name
if (!PKG_NAME) { console.error('X package.json 缺少 name'); process.exit(1) }
if (!existsSync(SRC)) { console.error('X 找不到 preset/ 目录: ' + SRC); process.exit(1) }

const agentYml = readFileSync(join(SRC, 'agent.cordis.yml'), 'utf8')
const presetYml = readFileSync(join(SRC, 'preset.yml'), 'utf8')

const patch = `# docs-mode bundle —— 文书模式（技术文档撰写专员）
#
# 本文件由 tools/build.mjs 生成，请勿手工编辑：
#   改动模式定义 → preset/agent.cordis.yml
#   改动模式元数据 → preset/preset.yml
#   改动安装器逻辑 → lib/index.js
#
# 安装方式：bundle 加载时由本包的 lib/index.js（安装器）把 preset/ 部署到
#   $DSH_HOME/.agent-presets/docs/ —— 该目录是 @deepseek-ai/dsh-agent-presets
#   的默认 user root（includeUserRoot），所以重启后 roster 能扫到「文书模式」。
#
# 为什么不是「在 patch 里直接声明 preset」：
#   @deepseek-ai/dsh-agent-presets 是进程级 roster 服务，Config 只接受
#   default / roots / includeShippedRoot / includeUserRoot —— 在 bundle 里 insert
#   单个 preset 的 id/name/plugins 既不是它的 schema，也会与 host 的同名服务相撞。
#
# 技能路径：preset/agent.cordis.yml 的 customSkillDirs 用 '{{PRESET_DIR}}/skills'
#   占位符，安装器部署时替换成真实绝对路径（不依赖 !!js/baseUrl）。
- insert:
    - id: docs-mode-installer
      name: '${PKG_NAME}'
`

writeFileSync(join(REPO, 'cordis.patch.yml'), patch, 'utf8')
console.log('  · cordis.patch.yml  (UTF-8 无 BOM)')

// ── 结构自检 ────────────────────────────────────────────────────────────────
const problems = []
if (!/^- insert:/m.test(patch)) problems.push('patch 缺少顶层 insert')
if (!patch.includes('id: docs-mode-installer')) problems.push('patch 缺少安装器声明')
if (!patch.includes(`name: '${PKG_NAME}'`)) problems.push('安装器未指向本包')
if (!existsSync(join(REPO, 'lib', 'index.js'))) problems.push('缺少安装器 lib/index.js')
if (!existsSync(join(SRC, 'skills'))) problems.push('preset/skills 缺失')
if (!existsSync(join(SRC, 'assets'))) problems.push('preset/assets 缺失')
if (!agentYml.includes('{{PRESET_DIR}}/skills')) problems.push('customSkillDirs 占位符缺失（应为 {{PRESET_DIR}}/skills）')
if (agentYml.includes('new URL(') && agentYml.includes("'skills/', baseUrl")) problems.push('agent.cordis.yml 仍含 baseUrl 表达式（旧版不兼容）')
if (!presetYml.includes('name:')) problems.push('preset.yml 缺少 name')

console.log('\n=== 自检 ===')
console.log(`  包名=${PKG_NAME}  版本=${pkg.version}`)
console.log(`  安装器=${existsSync(join(REPO, 'lib', 'index.js')) ? 'OK' : '缺失'}`)
console.log(`  customSkillDirs 占位符=${agentYml.includes('{{PRESET_DIR}}/skills') ? 'OK' : '缺失'}`)
console.log(`  patch 字节数=${Buffer.byteLength(patch, 'utf8')}`)
if (problems.length) {
  console.error('  ❌ ' + problems.join('; '))
  process.exit(1)
}
console.log('  ✅ 结构自检通过')
