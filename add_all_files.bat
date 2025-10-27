@echo off
echo Adding all files to Git repository...
echo.

cd /d "%~dp0"

"C:\Program Files\Git\cmd\git.exe" add .

echo.
echo Done! Now:
echo 1. Go back to GitHub Desktop
echo 2. Click the "Refresh" button or press Ctrl+R
echo 3. You should see ALL your files in the Changes tab
echo.

pause

