// docs-mode installer —— 把文书模式 preset 部署到 DSH 用户 preset 根。
// 安装方式：dsh plugin add <repo-or-package>
// 作用：将包内的 preset/ 目录内容复制到 $DSH_HOME/.agent-presets/docs/（缺省 ~/.dsh/.agent-presets/docs/），
//       复制完成后提示重启 DSH 使「文书模式」出现在模式选择器。
//
// 两个关键设计：
// 1) {{PRESET_DIR}} 占位符：preset/agent.cordis.yml 里 skill-filesystem 的
//    customSkillDirs 写的是 '{{PRESET_DIR}}/skills'，部署时替换成真实绝对路径。
//    这样既让随包技能被扫到，又不依赖 !!js/baseUrl（老版本 dsh 的 loader 在
//    preset 作用域可能不提供 baseUrl，求值失败会让整个 preset 挂载失败）。
// 2) 按版本号幂等：部署目录里写 .installed-version；版本不同才覆盖（升级自动生效），
//    相同则跳过，避免每次启动重复拷贝。设 DSH_DOCS_MODE_FORCE=1 可强制重部署。
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { homedir } from 'node:os'
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'

export const name = 'docs-mode-installer'

const here = dirname(fileURLToPath(import.meta.url))
const PRESET_SRC = resolve(here, '..', 'preset')

function dshHome() {
  return process.env.DSH_HOME || join(homedir(), '.dsh')
}

function pkgVersion() {
  try {
    const pkg = JSON.parse(readFileSync(join(here, '..', 'package.json'), 'utf8'))
    return pkg.version || '0.0.0'
  } catch {
    return '0.0.0'
  }
}

function deployFile(src, dest, presetDir) {
  let content = readFileSync(src, 'utf8')
  // 统一成正斜杠：cordis 的路径解析与跨平台都更稳
  content = content.split('{{PRESET_DIR}}').join(presetDir.replace(/\\/g, '/'))
  writeFileSync(dest, content, 'utf8')
}

function installPreset() {
  if (!existsSync(PRESET_SRC)) {
    console.error('[docs-mode] preset 资源缺失：' + PRESET_SRC)
    return
  }
  const dest = join(dshHome(), '.agent-presets', 'docs')
  const version = pkgVersion()
  const versionFile = join(dest, '.installed-version')
  const installed = existsSync(versionFile) ? readFileSync(versionFile, 'utf8').trim() : ''
  const force = process.env.DSH_DOCS_MODE_FORCE === '1'
  if (existsSync(dest) && installed === version && !force) {
    console.log(`[docs-mode] 文书模式已是最新 ${version}（跳过部署）`)
    return
  }
  mkdirSync(dest, { recursive: true })
  for (const entry of readdirSync(PRESET_SRC)) {
    const src = join(PRESET_SRC, entry)
    const dst = join(dest, entry)
    if (entry === 'agent.cordis.yml') {
      // 模式定义：总是替换占位符后写入（升级时自动修正旧版 !!js 残留）
      deployFile(src, dst, dest)
    } else {
      cpSync(src, dst, { recursive: true, force: true })
    }
  }
  writeFileSync(versionFile, version, 'utf8')
  console.log(`[docs-mode] 文书模式 ${version} 已部署到 ${dest}`)
  console.log('[docs-mode] 请重启 DSH 后，在模式选择器中选择「文书模式」')
}

export function apply(ctx) {
  try {
    installPreset()
  } catch (error) {
    console.error('[docs-mode] 部署失败：' + (error && error.message ? error.message : String(error)))
  }
  ctx.on('dispose', () => {
    // 不卸载已部署的文件——preset 是用户资产，卸载插件不影响已安装的模式
  })
}
