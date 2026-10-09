@echo off
REM 三段划分落盘 / 一致性检查 / 物理封印（M2）
REM 用法: run_split.cmd            生成 tasks/*/split.json 并封印 sealed/
REM       run_split.cmd --check    只重算并与已落盘结果比对（验收：重跑完全一致）
setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
pushd "%ROOT%"
"%PY%" -X utf8 -m formula_agh split --tasks "tasks" --sealed "sealed" %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
