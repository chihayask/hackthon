@echo off
REM 修复 AGH 因目录不私有而无法读取凭证的问题（本机反复出现）。
REM
REM 症状：任何 AGH 命令都以
REM     local daemon scope resolution failed: The credential store is unavailable.
REM 结束；doctor storage 正常、doctor profile 失败。
REM
REM 原因：%USERPROFILE%\.agh 上被加了一条沙箱用户组 CodexSandboxUsers 的
REM 访问控制项，使 AGH 的 hasPrivateDacl(~/.agh) 判定为 false，
REM 于是私有文件强制校验把凭证库当成不可用。
REM
REM 为什么做成脚本：2026-10-10 手工移除过一次，2026-10-12 又复发了——
REM 运行在沙箱里的进程访问该目录时会重新加上这条 ACE。
REM 所以这不是一次性修复，而是需要时可重跑的维护动作。
REM
REM 用法：  harness\fix_agh_acl.cmd
setlocal
set AGGH=%USERPROFILE%\.agh
if not exist "%AGGH%" ( echo [skip] %AGGH% 不存在 & exit /b 0 )
for /f "usebackq tokens=*" %%s in (`powershell -NoProfile -Command "(Get-LocalGroup -Name CodexSandboxUsers -ErrorAction SilentlyContinue).SID.Value"`) do set SID=%%s
if "%SID%"=="" ( echo [skip] 本机没有 CodexSandboxUsers 组 & exit /b 0 )
echo 移除 %AGGH% 上的 CodexSandboxUsers ACE (SID=%SID%)
icacls "%AGGH%" /remove:g *%SID%
echo.
echo 移除后的访问控制项：
icacls "%AGGH%"
exit /b 0