# AGH build preflight check (Windows)
# Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File harness\agh_preflight.ps1
# Read-only: inspects the machine, changes nothing.

$ErrorActionPreference = 'Continue'
$script:pass = 0
$script:fail = 0

function Check {
    param([string]$Name, [bool]$Ok, [string]$Detail, [string]$Fix)
    if ($Ok) {
        Write-Host ('[PASS] ' + $Name + ' -- ' + $Detail) -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host ('[MISS] ' + $Name + ' -- ' + $Detail) -ForegroundColor Red
        Write-Host ('       fix: ' + $Fix) -ForegroundColor Yellow
        $script:fail++
    }
}

Write-Host '===== AGH build preflight =====' -ForegroundColor Cyan

# 1) Node >= 24.10
$nodeExe = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
$nodeOk = $false
$nodeVer = 'not installed'
if ($nodeExe) {
    $nodeVer = (& $nodeExe -p 'process.versions.node')
    $parts = $nodeVer.Split('.')
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    $nodeOk = ($major -gt 24) -or (($major -eq 24) -and ($minor -ge 10))
}
Check -Name 'Node.js >= 24.10' -Ok $nodeOk -Detail ('found: ' + $nodeVer) -Fix 'install Node.js 24 LTS or newer'

# 2) corepack
$corepack = (Get-Command corepack -ErrorAction SilentlyContinue).Source
$cpDetail = 'not found'
if ($corepack) { $cpDetail = $corepack }
Check -Name 'corepack' -Ok ([bool]$corepack) -Detail $cpDetail -Fix 'npm i -g corepack'

# 3) git
$git = (Get-Command git.exe -ErrorAction SilentlyContinue).Source
$gitDetail = 'not found'
if ($git) { $gitDetail = $git }
Check -Name 'git' -Ok ([bool]$git) -Detail $gitDetail -Fix 'install Git for Windows'

# 4) npm registry reachability (use a China mirror when needed)
$ProgressPreference = 'SilentlyContinue'
$regOk = $false
$regDetail = ''
try {
    $r = Invoke-WebRequest -Uri 'https://registry.npmmirror.com/pnpm/10.34.5' -UseBasicParsing -TimeoutSec 15
    $regOk = ($r.StatusCode -eq 200)
    $regDetail = 'npmmirror reachable'
} catch {
    $regDetail = 'npmmirror unreachable'
}
Check -Name 'npm registry reachable' -Ok $regOk -Detail $regDetail -Fix 'npm config set registry https://registry.npmmirror.com'

# 5) MSVC C++ compiler (required for AGH native modules)
$cl = Get-ChildItem 'C:\Program Files*\Microsoft Visual Studio' -Recurse -Filter 'cl.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
$clDetail = 'cl.exe not found'
if ($cl) { $clDetail = $cl.FullName }
Check -Name 'MSVC C++ compiler' -Ok ([bool]$cl) -Detail $clDetail -Fix 'install Visual Studio Build Tools 2022 with Desktop development with C++'

# 6) Windows SDK
$sdk = Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\Include' -ErrorAction SilentlyContinue | Select-Object -First 1
$sdkDetail = 'Windows Kits\10\Include not found'
if ($sdk) { $sdkDetail = $sdk.FullName }
Check -Name 'Windows SDK 10' -Ok ([bool]$sdk) -Detail $sdkDetail -Fix 'select Windows 10/11 SDK in the VS Build Tools installer'

# 7) node-gyp bundled with npm
$npmCmd = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
$gyp = $null
if ($npmCmd) {
    $npmDir = Split-Path $npmCmd
    $gyp = Join-Path $npmDir 'node_modules/npm/node_modules/node-gyp/bin/node-gyp.js'
}
$gypOk = $false
$gypDetail = 'not found'
if ($gyp -and (Test-Path $gyp)) { $gypOk = $true; $gypDetail = $gyp }
Check -Name 'node-gyp (bundled)' -Ok $gypOk -Detail $gypDetail -Fix 'reinstall Node.js including npm'

Write-Host ''
Write-Host ('result: pass=' + $script:pass + '  missing=' + $script:fail) -ForegroundColor Cyan
if ($script:fail -gt 0) {
    Write-Host 'VERDICT: this machine cannot build AGH yet.' -ForegroundColor Yellow
    Write-Host 'Install the missing components above, or use the WSL2 path in docs/AGH_Windows_Build_Report.md' -ForegroundColor Yellow
    exit 1
}
Write-Host 'VERDICT: environment is ready. Follow docs/AGH_Windows_Build_Report.md' -ForegroundColor Green
exit 0