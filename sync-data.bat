@echo off
REM Change to the directory where this script lives
cd /d %~dp0

REM Copy web\data.js to web2\public\data.js
copy /Y ".\web\data.js" ".\web2\public\data.js"

echo Synced web\data.js to web2\public\data.js
pause
