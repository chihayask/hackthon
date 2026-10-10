@echo off
REM 把验证引擎打包成 Windows 可执行文件（目标机不需要装 Python）。
REM
REM 用法：  packaging\build_exe.cmd              :: 单文件 dist\formula_agh.exe
REM         packaging\build_exe.cmd onedir       :: 目录式 dist_onedir\formula_agh_onedir\
REM
REM 依赖：pip install pyinstaller（实测 6.22.3 / Python 3.13.5 / numpy 2.4.6）
REM 注意：--add-data 必须用绝对路径，否则会被按 --specpath 目录解析而找不到文件。
setlocal
set ROOT=%~dp0..
set MODE=%~1
if "%MODE%"=="" set MODE=onefile
pushd "%ROOT%"

if /I "%MODE%"=="onedir" (
  set NAME=formula_agh_onedir
  set LAYOUT=--onedir
  set DIST=dist_onedir
  set WORK=build_onedir
) else (
  set NAME=formula_agh
  set LAYOUT=--onefile
  set DIST=dist
  set WORK=build
)

python -m PyInstaller --noconfirm --clean %LAYOUT% ^
  --name %NAME% ^
  --paths src ^
  --add-data "%ROOT%\config\agent.yaml;config" ^
  --distpath %DIST% ^
  --workpath %WORK% ^
  --specpath %WORK% ^
  packaging\entry_cli.py

set RC=%ERRORLEVEL%
popd
echo.
if %RC%==0 (echo built %MODE%: %ROOT%\%DIST%\%NAME%) else (echo BUILD FAILED mode=%MODE% rc=%RC%)
exit /b %RC%
