@echo off
REM 单任务验证：AGH 通过命令工具调用本脚本。
REM 用法: run_verify.cmd <task_id> "<公式>" [自由参数,逗号分隔] [run_id]
REM
REM 三件事在这里一起保证：
REM   1. PYTHONPATH 指向 src，让 python -m formula_agh 可用；
REM   2. FORMULA_AGH_AUTOARCHIVE=1，验证一结束就自动归档进 evidence/ 并更新索引
REM      （归档是纪律，由脚本保证，不依赖智能体记得去调用归档命令）；
REM   3. FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm，把"假设来自 AGH 里的模型"如实写进 run.json。
REM      少了第 3 条，模型自主提出的公式会被记成 cli（人工给出），从而不计入评分脚本的
REM      「智能体发现」层——证据会在关键结论上说反话。这是第一次真实 AGH 运行后
REM      核对证据时发现的缺口。人工调试想改标，先 set FORMULA_AGH_HYPOTHESIS_SOURCE=cli。

setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
set FORMULA_AGH_AUTOARCHIVE=1
set FORMULA_AGH_RUNS=runs
set FORMULA_AGH_EVIDENCE=evidence
if "%FORMULA_AGH_HYPOTHESIS_SOURCE%"=="" set FORMULA_AGH_HYPOTHESIS_SOURCE=agh-llm
pushd "%ROOT%"
if "%~4"=="" (
  "%PY%" -X utf8 -m formula_agh verify --task "tasks/%~1" --formula "%~2" --params "%~3" --out "runs"
) else (
  "%PY%" -X utf8 -m formula_agh verify --task "tasks/%~1" --formula "%~2" --params "%~3" --run-id "%~4" --out "runs"
)
set RC=%ERRORLEVEL%
popd
exit /b %RC%