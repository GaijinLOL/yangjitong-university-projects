@echo off
rem ============================================================
rem  Curtains3 Defect Detection - CPU Launcher
rem  Usage: run_cpu.bat predict.py --source samples --json
rem         run_cpu.bat predict.py --selfcheck
rem  Note: prefers bundled runtime_cpu; falls back to system Python.
rem ============================================================
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set HERE=%~dp0
set PY=%HERE%runtime_cpu\python.exe

if exist "%PY%" goto run
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 找不到运行环境：既没有 runtime_cpu\python.exe，系统也没有 Python。
  echo        请恢复 runtime_cpu 文件夹，或安装 Python 3.10+ 并执行:
  echo        pip install -r requirements\requirements-cpu.txt
  exit /b 1
)
set PY=python

:run
"%PY%" %*
exit /b %ERRORLEVEL%
