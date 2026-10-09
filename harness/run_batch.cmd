@echo off
REM 批量验证：遍历 tasks/ 下所有含 candidates.json 的任务。
REM 批量模式不逐条自动归档（代价高），由流水线的归档步骤统一处理。

setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
pushd "%ROOT%"
if "%~1"=="" (
  "%PY%" -X utf8 -m formula_agh batch --tasks "tasks" --out "runs"
) else (
  "%PY%" -X utf8 -m formula_agh batch --tasks "tasks" --out "runs" --layer "%~1"
)
set RC=%ERRORLEVEL%
popd
exit /b %RC%
