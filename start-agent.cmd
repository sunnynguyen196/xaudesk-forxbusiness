@echo off
cd /d "%~dp0"
if not defined XAU_CLOUD_URL echo Please set XAU_CLOUD_URL to https://your-service.onrender.com & pause & exit /b 1
if not defined XAU_INGEST_TOKEN echo Please set XAU_INGEST_TOKEN & pause & exit /b 1
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" mt5_agent.py
) else (
  py -3.14 mt5_agent.py
)
pause
