# -*- coding: utf-8 -*-
# 仿真任务线的 AGH 驱动脚本。
#
# 与 harness/run_agent_discovery.ps1 同一套纪律：
#   1) 运行前用 examples/model_guard.py 校验模型路由全部为 Agnes，否则拒绝运行；
#   2) 每次运行建带时间戳的全新工作区（AGH 会话键由 cwd 派生，复用目录会串上下文）；
#   3) 预建会话取 sessionId，写进工作区握手文件（AGH 的 shell 工具不继承父进程环境变量）；
#   4) 结束后导出 AGH 原生轨迹供人工核查。
#
# 提示词放在 sim/agent_prompt.md（独立文件，便于修改，也避免 PowerShell here-string 解析问题）。
param(
  [string]$ProjectRoot = '',
  [string]$AghEntry = '',
  [string]$WorkRoot = '',
  [string]$SessionOut = '',
  [int]$MaxRounds = 4,
  [switch]$DryRun = $false
)

$ErrorActionPreference = 'Continue'
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
if ([string]::IsNullOrWhiteSpace($WorkRoot)) { $WorkRoot = Join-Path $env:TEMP 'agh-sim' }
if ([string]::IsNullOrWhiteSpace($SessionOut)) { $SessionOut = Join-Path $ProjectRoot 'evidence/agh-sessions' }
if ([string]::IsNullOrWhiteSpace($AghEntry)) {
  $candidate = Join-Path (Split-Path $ProjectRoot -Parent) 'agnes-harness/packages/cli/dist/local/agnes.mjs'
  if (Test-Path -LiteralPath $candidate) { $AghEntry = $candidate }
}
if (-not (Test-Path -LiteralPath $AghEntry)) { throw "AGH 入口不存在: $AghEntry" }
New-Item -ItemType Directory -Force -Path $SessionOut | Out-Null
# --- 0) 代理自检：环境里的代理若没人监听，就让 AGH 直连 ---
# 2026-10-12 实测的失败模式：HTTP(S)_PROXY 指向一个已关闭的本地代理时，
# AGH 的**守护进程**会在带毒环境下启动，此后所有推理都以 TRANSPORT 失败；
# 而 doctor provider --probe 是**进程内**执行，却显示一切正常——两者矛盾，极难察觉。
# 这里探测代理端口：不通就清空代理变量（只影响本进程及其子进程，不改系统设置）。
$proxyVars = @('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy')
$rawProxy = $env:HTTPS_PROXY
if (-not [string]::IsNullOrWhiteSpace($rawProxy)) {
  $alive = $false
  try {
    $uri = [System.Uri]$rawProxy
    $client = New-Object System.Net.Sockets.TcpClient
    $client.Connect($uri.Host, $uri.Port)
    $alive = $client.Connected
    $client.Close()
  } catch { $alive = $false }
  if (-not $alive) {
    Write-Host ("[warn] 代理 " + $rawProxy + " 无人监听，本次 AGH 运行将直连（已清空代理变量）")
    foreach ($n in $proxyVars) { Remove-Item ("Env:" + $n) -ErrorAction SilentlyContinue }
    $env:NO_PROXY = '*'
    # 守护进程若已在带毒环境下启动，必须先停掉，否则它仍会用死代理。
    try { & node $AghEntry daemon stop 2>&1 | Out-Null; Start-Sleep -Seconds 2 } catch {}
  }
}

# --- 1) 路由守卫 ---
$guard = Join-Path $ProjectRoot 'examples/model_guard.py'
if (Test-Path -LiteralPath $guard) {
  & python $guard
  if ($LASTEXITCODE -ne 0) { throw "模型路由校验失败，拒绝运行 (exit=$LASTEXITCODE)" }
} else { Write-Host '[warn] 找不到 examples/model_guard.py' }

# --- 2) 全新工作区（只放智能体该看到的） ---
$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss')
$work = Join-Path $WorkRoot ('sim-inversion-' + $stamp)
New-Item -ItemType Directory -Force -Path (Join-Path $work 'sim/data') | Out-Null
foreach ($f in @('ebm.py', 'invert.py', 'probe.py')) {
  Copy-Item -LiteralPath (Join-Path $ProjectRoot (Join-Path 'sim' $f)) -Destination (Join-Path $work 'sim') -Force
}
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'sim/data/zonal_bands.csv') -Destination (Join-Path $work 'sim/data') -Force

# --- 3) 提示词（从文件读，并把工具路径填进去） ---
# python 的完整路径含空格（deepseek harness workspace），而 AGH 的审批规则要求包装脚本',
# 以无空格绝对路径调用；工作区本身在无空格路径下，所以在这里生成一个 probe.cmd 包装。
$promptPath = Join-Path $ProjectRoot 'sim/agent_prompt.md'
$python = (Get-Command python).Source
$wrapper = Join-Path $work 'sim/probe.cmd'
$wrapperBody = '@echo off' + "`r`n" + '"' + $python + '" "%~dp0probe.py" %*' + "`r`n"
[System.IO.File]::WriteAllText($wrapper, $wrapperBody, (New-Object System.Text.UTF8Encoding($false)))
$prompt = Get-Content -LiteralPath $promptPath -Raw -Encoding UTF8
$prompt = $prompt.Replace('{{PROBE}}', $wrapper)
$prompt = $prompt.Replace('{{MAXROUNDS}}', [string]$MaxRounds)

# --- 4) 会话与握手 ---
$env:FORMULA_AGH_HYPOTHESIS_SOURCE = 'agh-llm'
$sessionId = ''
if ($DryRun) {
  $sessionId = '(dry-run)'
} else {
  try {
    & node $AghEntry -p '就绪确认：只回复 ok' --mode json --cwd $work 2>&1 | Out-Null
    $sessionsJson = & node $AghEntry sessions --json 2>&1 | Out-String
    $parsed = $sessionsJson | ConvertFrom-Json
    $match = $parsed.items | Where-Object { $_.cwd -eq $work } | Select-Object -First 1
    if ($match) { $sessionId = [string]$match.sessionId }
  } catch { Write-Host ('[warn] 预建会话失败: ' + $_.Exception.Message) }
}
$env:FORMULA_AGH_SESSION_ID = $sessionId
$env:FORMULA_AGH_AGENT_WORKSPACE = $work
$provLine = 'agh-llm ' + $sessionId
foreach ($dir in @($work, (Join-Path $work 'sim'))) {
  if (Test-Path -LiteralPath $dir) {
    [System.IO.File]::WriteAllText((Join-Path $dir '_agh_provenance.txt'), $provLine, (New-Object System.Text.UTF8Encoding($false)))
  }
}

# --- 5) 调用模型 ---
$outFile = Join-Path $SessionOut ('sim-inversion-' + $stamp + '.json')
if ($DryRun) {
  Write-Host ('[dry ] 工作区 ' + $work)
  Write-Host ('[dry ] 会话 ' + $sessionId)
  Write-Host ('[dry ] 提示词前 200 字: ' + $prompt.Substring(0, [Math]::Min(200, $prompt.Length)))
  [System.IO.File]::WriteAllText($outFile, '{"dry_run": true}', (New-Object System.Text.UTF8Encoding($false)))
  return
}
Write-Host '[run ] 调用 AGH 做参数反演 ...'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$raw = & node $AghEntry -p $prompt --mode json --cwd $work 2>&1 | Out-String
$code = $LASTEXITCODE
$sw.Stop()
[System.IO.File]::WriteAllText($outFile, $raw, (New-Object System.Text.UTF8Encoding($false)))
Write-Host ("[done] exit=$code  {0:n1}s" -f $sw.Elapsed.TotalSeconds)
Write-Host ('会话: ' + $sessionId)
Write-Host ('记录: ' + $outFile)