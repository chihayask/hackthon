@echo off
REM 一键复现（M2）：契约校验 -> 划分 -> 单测 -> 金标准 -> 判别力 -> 候选 ->
REM                判别力报告 -> 尺度检验 -> 负对照 -> 对抗性 -> 独立复算 ->
REM                评分对照 -> 证据归档，最后与基线指纹逐字段比对。
REM 用法:
REM   run_reproduce.cmd                 在当前目录复现并与基线比对
REM   run_reproduce.cmd --update-baseline
REM   run_reproduce.cmd --clean D:\repro

setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
pushd "%ROOT%"
"%PY%" -X utf8 reproduce.py %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
