@echo off
cd /d "%~dp0"

echo Starting Django server...
start "" python manage.py runserver

timeout /t 3

echo Opening Django Admin in Chrome...

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://127.0.0.1:8000/admin"

exit