@echo off
fltmc >nul 2>&1
if errorlevel 1 (
	echo Requesting Administrator privileges...
	powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
	exit /b
)

echo ========================================
echo    WiFi Firewall Control Panel
echo ========================================
echo.
echo Starting dashboard...
echo.
echo IMPORTANT: Make sure you run this as Administrator!
echo.
python "%~dp0firewall_dashboard.py"
pause
