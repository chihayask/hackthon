@echo off
REM 一键复现（M2 交付）：从数据契约校验一路跑到证据归档，并与基线指纹比对。
REM 用法:
REM   reproduce.cmd                 在当前目录复现
REM   reproduce.cmd --update-baseline  固化基线
REM   reproduce.cmd --clean D:\repro   干净目录复现
setlocal
set ROOT=%~dp0
set PY=%ROOT%.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%src
pushd "%ROOT%"
"%PY%" -X utf8 reproduce.py %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
