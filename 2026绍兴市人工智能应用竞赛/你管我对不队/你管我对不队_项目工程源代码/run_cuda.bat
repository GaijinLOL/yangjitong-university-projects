@echo off
rem ============================================================
rem  Curtains3 Defect Detection - CUDA Launcher (NVIDIA GPU)
rem  Usage: run_cuda.bat predict.py --source samples --json
rem         run_cuda.bat predict.py --selfcheck
rem  Note: CUDA runtime (~4.6 GB) is NOT bundled. Install it first:
rem        pip install -r requirements\requirements-cuda.txt --index-url https://download.pytorch.org/whl/cu118
rem ============================================================
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set HERE=%~dp0
set PY=%HERE%runtime_cuda\python.exe

if exist "%PY%" goto run
where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 找不到运行环境。CUDA 运行时不随包提供：
  echo        请安装 Python 3.10+，并执行
  echo        pip install -r requirements\requirements-cuda.txt --index-url https://download.pytorch.org/whl/cu118
  echo        （需 NVIDIA 驱动 >= 522.06；无独显请改用 run_cpu.bat）
  exit /b 1
)
set PY=python

:run
"%PY%" %*
exit /b %ERRORLEVEL%
