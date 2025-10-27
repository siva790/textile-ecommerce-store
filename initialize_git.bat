@echo off
echo ================================================
echo   Initializing Git for Textile E-Commerce
echo ================================================
echo.

cd /d "%~dp0"

echo Current directory: %CD%
echo.

echo Step 1: Checking Git installation...
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Git command line is not available.
    echo Please use GitHub Desktop to add this repository.
    echo.
    echo Instructions:
    echo 1. Open GitHub Desktop
    echo 2. Click "Add an Existing Repository"
    echo 3. Choose this folder: %CD%
    echo 4. If it asks to create repository, click "create a repository"
    echo 5. Then click "Publish repository"
    echo.
    pause
    exit /b 1
)

echo Git found!
echo.

echo Step 2: Initializing Git repository...
git init

echo.
echo Step 3: Adding all files (respecting .gitignore)...
git add .

echo.
echo Step 4: Checking status...
git status

echo.
echo Step 5: Creating first commit...
git commit -m "Initial commit: Textile E-Commerce Store"

echo.
echo ================================================
echo   SUCCESS! Git repository initialized!
echo ================================================
echo.
echo Next steps:
echo 1. Open GitHub Desktop
echo 2. Add this repository
echo 3. Publish to GitHub
echo.

pause

