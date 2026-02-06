@echo off
echo ==========================================
echo    NEUTRON - Automatic GitHub Uploader
echo ==========================================
echo.

echo [1/3] Adding files...
git add .

echo.
echo [2/3] Committing changes...
git commit -m "Auto update: %date% %time%"

echo.
echo [3/3] Pushing to GitHub...
git push origin main

echo.
echo ==========================================
echo              Upload Complete!
echo ==========================================
pause
