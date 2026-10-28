<#
.SYNOPSIS
  更新 docs-mode 到最新，并同步到 DSH profile（解决 file: 安装副本不同步的坑）。

.DESCRIPTION
  根据 profile 的安装方式自动选择路径：
    - file: 安装（开发调试）→ 把本仓库内容同步到 node_modules/dsh-docs-mode，
      并清除 package.json 的 UTF-8 BOM（BOM 会让 bundle 被静默跳过）
    - npm / github 安装（普通用户）→ 提示用 dsh plugin add 重装

  完成后自动跑 doctor 诊断，并提示重启 DSH。

.PARAMETER Profile
  要更新的 DSH profile，默认 desktop。

.PARAMETER Source
  file: 安装时使用的源目录；默认为本脚本所在仓库。

.PARAMETER NoPull
  跳过 git pull（源目录不是 git 仓库或不想联网时用）。

.EXAMPLE
  .\update.ps1
  .\update.ps1 -Profile web
  .\update.ps1 -Source D:\work\docs-mode -NoPull
#>
param(
  [string]$Profile = 'desktop',
  [string]$Source,
  [switch]$NoPull
)

$ErrorActionPreference = 'Stop'
function Info($m) { Write-Host "  $m" }
function OK($m)   { Write-Host "  ✅ $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  ⚠️  $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "  ❌ $m" -ForegroundColor Red }

# ── 定位仓库与 profile ────────────────────────────────────────────────────
$Repo = if (Test-Path (Join-Path $PSScriptRoot 'package.json')) { $PSScriptRoot } else { Split-Path $PSScriptRoot -Parent }
$DSH_HOME = if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $HOME '.dsh' }
$ProfileDir = Join-Path $DSH_HOME "profiles/$Profile"
$Installed  = Join-Path $ProfileDir 'node_modules/dsh-docs-mode'
$ProfilePkg = Join-Path $ProfileDir 'package.json'

Write-Host "`n=== docs-mode 更新 ===" -ForegroundColor Cyan
Info "仓库:   $Repo"
Info "profile: $Profile"
Info "DSH_HOME: $DSH_HOME"

if (-not (Test-Path $ProfilePkg)) {
  Fail "找不到 profile：$ProfileDir"
  exit 1
}

# ── 判断安装方式 ──────────────────────────────────────────────────────────
$dep = $null
try {
  $pkg = Get-Content $ProfilePkg -Raw -Encoding UTF8 | ConvertFrom-Json
  $dep = $pkg.dependencies.'dsh-docs-mode'
} catch {
  Warn "profile package.json 解析失败（可能也是 BOM 问题），按 file: 处理"
}

Write-Host "`n▶ 安装方式: $(if ($dep) { $dep } else { '未知（按 file: 处理）' })"

if ($dep -and -not $dep.StartsWith('file:')) {
  # npm / github 源安装：交给 dsh plugin 重装
  Write-Host "`n▶ 非 file: 安装，使用 dsh plugin 重装" -ForegroundColor Cyan
  $spec = if ($dep.StartsWith('github:') -or $dep.StartsWith('http')) { $dep } else { "dsh-docs-mode" }
  Write-Host "  执行: dsh plugin --profile $Profile add $spec"
  & dsh plugin --profile $Profile add $spec
  if ($LASTEXITCODE -ne 0) { Fail "重装失败"; exit 1 }
  OK "已重装 $spec"
} else {
  # file: 安装：同步源 → node_modules
  Write-Host "`n▶ 同步源目录到 node_modules" -ForegroundColor Cyan
  $Src = if ($Source) { $Source } elseif ($dep) { $dep.Substring('file:'.Length) } else { $Repo }
  if (-not (Test-Path (Join-Path $Src 'package.json'))) {
    Fail "源目录无效：$Src"
    exit 1
  }
  Info "源: $Src"

  # 可选 git pull
  if (-not $NoPull -and (Test-Path (Join-Path $Src '.git'))) {
    Info "git pull..."
    $prevEA = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $null = & git -C $Src pull 2>&1
    $pullCode = $LASTEXITCODE
    $ErrorActionPreference = $prevEA
    if ($pullCode -eq 0) { OK "git pull 完成" } else { Warn "git pull 失败（继续使用本地版本）" }
  }

  # 清空并复制（保留 .git）
  if (Test-Path $Installed) {
    Get-ChildItem $Installed -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  }
  New-Item -ItemType Directory -Path $Installed -Force | Out-Null
  Get-ChildItem $Src -Force |
    Where-Object { $_.Name -ne '.git' -and $_.Name -notlike '*.tgz' } |
    ForEach-Object { Copy-Item $_.FullName $Installed -Recurse -Force }
  OK "已同步到 $Installed"

  # 去 BOM
  $pkgPath = Join-Path $Installed 'package.json'
  if (Test-Path $pkgPath) {
    $bytes = [System.IO.File]::ReadAllBytes($pkgPath)
    if ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
      [System.IO.File]::WriteAllBytes($pkgPath, $bytes[3..($bytes.Length - 1)])
      OK "已清除 package.json 的 BOM"
    } else {
      OK "package.json 无 BOM"
    }
  }
}

# ── 版本确认 ──────────────────────────────────────────────────────────────
$ver = '未知'
try { $ver = (Get-Content (Join-Path $Installed 'package.json') -Raw -Encoding UTF8 | ConvertFrom-Json).version } catch {}
Write-Host "`n▶ 当前安装版本: $ver" -ForegroundColor Cyan

# ── 跑 doctor 自检 ────────────────────────────────────────────────────────
$doctor = Join-Path $Repo 'tools/doctor.mjs'
if (Test-Path $doctor) {
  Write-Host "`n▶ doctor 自检" -ForegroundColor Cyan
  & node $doctor --profile $Profile
  $doctorOk = $LASTEXITCODE -eq 0
} else {
  Warn "未找到 tools/doctor.mjs，跳过自检"
  $doctorOk = $null
}

# ── 结论 ──────────────────────────────────────────────────────────────────
Write-Host "`n=== 完成 ===" -ForegroundColor Cyan
if ($doctorOk -eq $false) {
  Warn "doctor 报告了问题，请按上面的提示修复后重启 DSH"
} else {
  OK "更新完成。请【彻底退出 DSH】（任务管理器确认无 DeepSeek Harness.exe 进程）再启动。"
}
