@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Execute instalar.ps1 para preparar o ambiente Python.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "%~dp0main.py"
