@echo off
REM 与标准答案对照（M2 评分，独立于智能体进程）
setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
pushd "%ROOT%"
"%PY%" -X utf8 "src/scoring/compare.py" --runs "runs" --tasks "tasks" --reference "reference" --out "evidence/scoring" %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
