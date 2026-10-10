@echo off
REM 单任务验证：AGH 通过命令工具调用本脚本。
REM 用法: run_verify.cmd <task_id> "<公式>" [自由参数,逗号分隔] [run_id]
REM
REM 三件事在这里一起保证：
REM   1. PYTHONPATH 指向 src，让 python -m formula_agh 可用；
REM   2. FORMULA_AGH_AUTOARCHIVE=1，验证一结束就自动归档进 evidence/ 并更新索引
REM      （归档是纪律，由脚本保证，不依赖智能体记得去调用归档命令）；
REM   3. **故意不设**假设来源。
REM      旧版本在这里写 set FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm，等于把"脚本被调用"
REM      直接当成"模型自主发现"：任何人手工敲一条 run_verify.cmd 都会留下 agh-llm 证据。
REM      外部审计（2026-10-10）把这条列为可达的误标路径，已移除。
REM      现在来源由**调用方**显式声明：harness/run_agent_discovery.ps1 会 export
REM      FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm 与 FORMULA_AGH_SESSION_ID；两者都到位，
REM      run.json 的 provenance_bound 才为 true。人工调试默认记 cli（诚实）。

setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
set FORMULA_AGH_AUTOARCHIVE=1
set FORMULA_AGH_RUNS=runs
set FORMULA_AGH_EVIDENCE=evidence
REM --- 来源与会话号：握手文件而不是环境变量 ---------------------------------------
REM 实测（2026-10-10）：AGH 的 shell 工具**不继承**驱动进程的环境变量，所以
REM 驱动脚本 export 的 FORMULA_AGH_HYPOTHESIS_SOURCE / _SESSION_ID 传不到这里，
REM 22 条自主运行被记成了 cli（保守但错误）。改为在工作区里放一个握手文件，
REM 由驱动脚本写入，本脚本从**当前目录**读。读不到就退回诚实默认（cli、无会话号）。
set "PROV_FILE=%CD%\_agh_provenance.txt"
if exist "%PROV_FILE%" (
  for /f "usebackq tokens=1,2,3" %%a in ("%PROV_FILE%") do (
    if "%FORMULA_AGH_HYPOTHESIS_SOURCE%"=="" set "FORMULA_AGH_HYPOTHESIS_SOURCE=%%a"
    if "%FORMULA_AGH_SESSION_ID%"=="" set "FORMULA_AGH_SESSION_ID=%%b"
    if "%FORMULA_AGH_AGENT_WORKSPACE%"=="" set "FORMULA_AGH_AGENT_WORKSPACE=%CD%"
    REM 第三个字段是消融开关：no-scale = 不把尺度检验的结论反馈给模型
    REM （尺度理由会写出目标幂次，本身也是一种先验）。
    echo %%c | findstr /I "no-scale" >nul && set "FORMULA_AGH_NO_SCALE=1"
  )
)
set "SCALE_ARG="
if /I "%FORMULA_AGH_NO_SCALE%"=="1" set "SCALE_ARG=--no-scale-check"
REM 引擎选择：默认用**源码** Python（与仓库一致，不会因为 exe 过期而与源码行为分叉）。
REM 打包的 exe 需要显式开启：set FORMULA_AGH_USE_EXE=1。
REM 教训（2026-10-10）：原先无条件优先 exe，结果源码加了 session_id/provenance_bound 后，
REM 包装脚本仍在跑旧 exe，新字段根本没写进 run.json——静默走了一条与源码不同的路径。
set "ENGINE="
if /I "%FORMULA_AGH_USE_EXE%"=="1" if exist "%ROOT%\dist_onedir\formula_agh_onedir\formula_agh_onedir.exe" set "ENGINE=%ROOT%\dist_onedir\formula_agh_onedir\formula_agh_onedir.exe"
if /I "%FORMULA_AGH_USE_EXE%"=="1" if not defined ENGINE if exist "%ROOT%\dist\formula_agh.exe" set "ENGINE=%ROOT%\dist\formula_agh.exe"

pushd "%ROOT%"
if not defined ENGINE set "ENGINE=%PY%"
if not defined ENGINE set "ENGINE=python"

if "%~4"=="" (
  if "%ENGINE%"=="%PY%" (
    "%PY%" -X utf8 -m formula_agh verify --task "tasks/%~1" --formula "%~2" --params "%~3" %SCALE_ARG% --out "runs"
  ) else if "%ENGINE%"=="python" (
    python -X utf8 -m formula_agh verify --task "tasks/%~1" --formula "%~2" --params "%~3" %SCALE_ARG% --out "runs"
  ) else (
    "%ENGINE%" verify --task "tasks/%~1" --formula "%~2" --params "%~3" %SCALE_ARG% --out "runs"
  )
) else (
  if "%ENGINE%"=="%PY%" (
    "%PY%" -X utf8 -m formula_agh verify --task "tasks/%~1" --formula "%~2" --params "%~3" %SCALE_ARG% --run-id "%~4" --out "runs"
  ) else if "%ENGINE%"=="python" (
    python -X utf8 -m formula_agh verify --task "tasks/%~1" --formula "%~2" --params "%~3" %SCALE_ARG% --run-id "%~4" --out "runs"
  ) else (
    "%ENGINE%" verify --task "tasks/%~1" --formula "%~2" --params "%~3" %SCALE_ARG% --run-id "%~4" --out "runs"
  )
)
set RC=%ERRORLEVEL%
popd
exit /b %RC%