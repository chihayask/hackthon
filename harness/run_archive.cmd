@echo off
REM 证据归档与双向孤儿检测（M2）
REM 用法: run_archive.cmd            归档 runs/ 到 evidence/ 并更新索引
REM       run_archive.cmd --check    只做孤儿检测
setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
pushd "%ROOT%"
"%PY%" -X utf8 -m formula_agh archive --runs "runs" --out "evidence" %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
