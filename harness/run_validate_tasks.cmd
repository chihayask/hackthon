@echo off
REM 任务集校验：格式、字段与答案泄漏检测
setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
pushd "%ROOT%"
"%PY%" -X utf8 -m formula_agh validate-tasks --tasks "tasks"
set RC=%ERRORLEVEL%
popd
exit /b %RC%