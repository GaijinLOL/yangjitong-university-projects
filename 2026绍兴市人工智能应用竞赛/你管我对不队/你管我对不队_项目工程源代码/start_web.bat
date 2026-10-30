@echo off
rem Note: prefers bundled runtime_cpu; falls back to system Python.
setlocal
cd /d %~dp0
chcp 65001 >nul
set PYTHONUTF8=1
set PY=%~dp0runtime_cpu\python.exe

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
"%PY%" backend\web_server.py --port 8080
