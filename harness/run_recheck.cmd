@echo off
REM 独立复算（M2）：对 runs/ 下每条运行重新划分、重新拟合、重新判定，再与记录比对
setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
pushd "%ROOT%"
"%PY%" -X utf8 -m formula_agh recheck --runs "runs" --tasks "tasks" --out "recheck" %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
