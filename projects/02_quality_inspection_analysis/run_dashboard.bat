@echo off
chcp 65001 > nul
echo =========================================================
echo  [Quality Intelligence Dashboard] Running System
echo =========================================================
echo 1. Running CLI Statistical Report...
python main.py
echo.
echo 2. Launching Streamlit Interactive Dashboard...
streamlit run app.py
pause
