// docs-mode installer —— 把文书模式 preset 部署到 DSH 用户 preset 根。
// 安装方式：dsh plugin add <repo-or-package>
// 作用：将包内的 preset/ 目录内容复制到 $DSH_HOME/.agent-presets/docs/（缺省 ~/.dsh/.agent-presets/docs/），
//       复制完成后提示重启 DSH 使「文书模式」出现在模式选择器。
// 幂等：目标已存在时不覆盖（除非 DSH_DOCS_MODE_FORCE=1），避免破坏用户已有修改。
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { homedir } from 'node:os'
import { cpSync, existsSync, mkdirSync, readdirSync } from 'node:fs'

export const name = 'docs-mode-installer'

const here = dirname(fileURLToPath(import.meta.url))
const PRESET_SRC = resolve(here, '..', 'preset')

function dshHome() {
  return process.env.DSH_HOME || join(homedir(), '.dsh')
}

function installPreset() {
  if (!existsSync(PRESET_SRC)) {
    console.error('[docs-mode] preset 资源缺失：' + PRESET_SRC)
    return
  }
  const dest = join(dshHome(), '.agent-presets', 'docs')
  const entries = readdirSync(PRESET_SRC)
  const force = process.env.DSH_DOCS_MODE_FORCE === '1'
  if (existsSync(dest) && !force) {
    console.log(`[docs-mode] 文书模式已存在于 ${dest}（跳过；如需强制覆盖设 DSH_DOCS_MODE_FORCE=1）`)
    return
  }
  mkdirSync(dest, { recursive: true })
  for (const entry of entries) {
    cpSync(join(PRESET_SRC, entry), join(dest, entry), { recursive: true, force: true })
  }
  console.log(`[docs-mode] 文书模式已部署到 ${dest}`)
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
