# run_agent_discovery.ps1 -- 让 AGH 里的模型自主完成「公式发现」任务（M1 编排）
#
# 每个任务在**独立工作目录**里跑，因此各自是一个独立 AGH 会话（会话键由 cwd 派生），
# 而不是把 22 个任务塞进同一个上下文。独立目录里**只放该任务对智能体可见的两个文件**
# （meta.json 与 data_train.csv），于是「不许看 sealed/ 与 reference/」从纪律变成结构：
# 那个目录里根本没有别的东西。
#
# 验证统一走 E:\fagh\harness\run_verify.cmd —— 它带 provenance（hypothesis_source=agh-llm）
# 并自动归档。注意 AGH 的审批校验器要求 allow 规则的 argv 以**绝对路径形状**开头，
# 所以包装脚本必须用绝对路径、不加引号、不加 & 调用；E:\fagh 是无空格的别名目录联接。
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File harness\run_agent_discovery.ps1 -Tasks phys-ohm,phys-weight
param(
  [string]$Tasks = '',
  [int]$MaxRounds = 3,
  [string]$ProjectRoot = '',
  [string]$AghEntry = 'E:\.dsh\deepseek harness workspace\agnes-harness\packages\cli\dist\local\agnes.mjs',
  [string]$WorkRoot = 'E:\agh-runs',
  [string]$SessionOut = '',
  [string]$Wrapper = 'E:\fagh\harness\run_verify.cmd'
)

$ErrorActionPreference = 'Continue'
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) { $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
if ([string]::IsNullOrWhiteSpace($SessionOut)) { $SessionOut = Join-Path $ProjectRoot 'evidence\agh-sessions' }
New-Item -ItemType Directory -Force -Path $SessionOut | Out-Null
if (-not (Test-Path -LiteralPath $AghEntry)) { throw "找不到 AGH 入口: $AghEntry" }

$env:AGNES_PROFILE = 'local-dev'
# 关键：不要用空壳 AGH_HOME。已配置并登录过的是默认的 ~\.agh。
Remove-Item Env:AGH_HOME -ErrorAction SilentlyContinue

$summary = @()
$taskList = ($Tasks -split '[,;\s]+') | Where-Object { $_ -ne '' }
foreach ($task in $taskList) {
  $task = $task.Trim()
  if ($task -eq '') { continue }
  $dataDir = Join-Path $ProjectRoot ("tasks\" + $task)
  if (-not (Test-Path -LiteralPath $dataDir)) { Write-Host "[skip] $task : 没有 tasks\$task"; continue }

  $work = Join-Path $WorkRoot $task
  $visible = Join-Path $work ("tasks\" + $task)
  New-Item -ItemType Directory -Force -Path $visible | Out-Null
  Copy-Item -LiteralPath (Join-Path $dataDir 'meta.json')      -Destination $visible -Force
  Copy-Item -LiteralPath (Join-Path $dataDir 'data_train.csv') -Destination $visible -Force

  $prompt = @"
你现在只处理一个任务：$task。工作目录就是你的工作区，里面只有 tasks\$task\meta.json 和 tasks\$task\data_train.csv。

只许读这两个文件。禁止读取 reference/、sealed/，以及任何名为 answer / ground_truth / solution 的文件。

按 formula-discovery-loop 技能执行，最多 $MaxRounds 轮。每轮：
1) 先用一句话声明本轮假设与依据（量纲 / 单调性 / 极限行为 / 上一轮失败原因）；
2) 然后执行下面这一条命令验证。必须原样照抄：绝对路径、不加引号、不加 & 、不要用 cmd /c 、
   不要加管道 | 、&& 或重定向：
   $Wrapper $task "<公式>" "<自由参数,逗号分隔>"
   自由参数以 meta.json 的 free_parameters 为准；若为空就写一对空双引号 ""。
3) 读取命令输出 JSON 里的 verdict 与 checks[]，看哪些项 passed=false；
   参数用法（最容易出错，务必看清）：
   * 第三个参数是**自由参数的名称列表**（逗号分隔），名字必须与 meta.json 的 free_parameters 完全一致；
     它**不是数值**。meta 写 ["sigma"] 就传 "sigma"，不要传 "5.67e-8"。
   * 若 free_parameters 非空，公式里必须把这些名字**当符号用**，拟合交给引擎。
     例：free_parameters=["sigma"] 时应写 `sigma*A*T**4` 并传 "sigma"；
     写成 `A*T**4`（拿已声明单位的 A 当系数）会被量纲门正确拒绝。
   * 若 free_parameters 为空，第三个参数写一对空双引号 ""。
4) 失败必须显式处理：dimension 或 scale-* 失败说明形状不对，必须换函数族，不要原地调参数；
   holdout / extrapolation 失败说明域内没拟合好或过拟合。每轮失败理由要写进下一轮假设。

若连续几轮都在同一族里打转，换族前先检查三件事（方法论，不是答案）：
(a) 是否有某个量出现在**分母或被开方**里（试 sqrt / 分母结构）；
(b) 小量极限是否被正确保留（例如小角度时 sin(x)≈x，但大角度不能近似）；
(c) 是否漏掉了 meta.json 里已声明的某个变量或自由参数。

硬性要求：每一轮都**必须真的执行**上面那条命令并把它的 JSON 结果作为依据；只在回答里写出公式而不调用验证器，视为本轮无效。
公式里幂次一律写成 ** ，不要写成 ^ （^ 在 Windows 命令行里是转义符）。参数与公式都必须用英文双引号成对闭合。

结束时用一段话给出：最终公式、最终判定、以及你是否推翻过自己（引用一次否决的原文理由）。
不要执行 run_verify.cmd 以外的任何 shell 命令。
"@

  $outFile = Join-Path $SessionOut ($task + '.json')
  Write-Host ("[run ] {0} ..." -f $task)
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  try {
    $raw = & node $AghEntry -p $prompt --mode json --cwd $work 2>&1 | Out-String
    $code = $LASTEXITCODE
  } catch {
    $raw = "EXCEPTION: " + $_.Exception.Message
    $code = -1
  }
  $sw.Stop()
  [System.IO.File]::WriteAllText($outFile, $raw, (New-Object System.Text.UTF8Encoding($false)))

  $verdict = 'unknown'
  if ($raw -match '"reason"\s*:\s*"([^"]+)"') { $verdict = $Matches[1] }
  Write-Host ("[done] {0}  exit={1} reason={2}  {3:n1}s" -f $task, $code, $verdict, $sw.Elapsed.TotalSeconds)
  $summary += [pscustomobject]@{ task = $task; exit = $code; reason = $verdict; seconds = [math]::Round($sw.Elapsed.TotalSeconds, 1) }
}

Write-Host ''
Write-Host '=== summary ==='
$summary | Format-Table -AutoSize | Out-String | Write-Host
($summary | Format-Table -AutoSize | Out-String) | Set-Content -LiteralPath (Join-Path $SessionOut '_summary.txt') -Encoding UTF8
Write-Host ("会话记录写入: " + $SessionOut)
