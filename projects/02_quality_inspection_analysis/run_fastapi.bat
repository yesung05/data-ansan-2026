@echo off
chcp 65001 > nul
echo =========================================================
echo  [Quality Intelligence FastAPI Backend]
echo =========================================================
cd backend
python run_server.py
pause
