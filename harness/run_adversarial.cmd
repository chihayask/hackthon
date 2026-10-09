@echo off
REM 对抗性测试套件（M2）：13 类"能让验证放水"的用例
setlocal
set ROOT=%~dp0..
set PY=%ROOT%\.venv\Scripts\python.exe
if not exist "%PY%" set PY=python
set PYTHONPATH=%ROOT%\src
pushd "%ROOT%"
"%PY%" -X utf8 "examples/adversarial_suite.py" %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
