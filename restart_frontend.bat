@echo off
echo ========================================
echo Restarting Next.js Frontend
echo ========================================
echo.

cd neuro-frontend

echo [1/4] Stopping any running Node processes...
taskkill /F /IM node.exe 2>nul
timeout /t 2 >nul

echo [2/4] Clearing Next.js cache...
if exist .next rmdir /s /q .next
echo Cache cleared!

echo [3/4] Clearing browser cache instructions:
echo    - Press Ctrl + Shift + R in your browser
echo    - Or open DevTools (F12) and right-click refresh button
echo    - Select "Empty Cache and Hard Reload"
echo.

echo [4/4] Starting dev server...
echo.
npm run dev
