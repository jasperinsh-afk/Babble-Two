@echo off
setlocal
set "NODE_DIR=%USERPROFILE%\.workbuddy\binaries\node\versions\22.22.2-6"
if not exist "%NODE_DIR%\node.exe" if exist "C:\Program Files\nodejs\node.exe" set "NODE_DIR=C:\Program Files\nodejs"
set "PATH=%NODE_DIR%;%PATH%"
cd /d "%~dp0"
echo [叭啦网页版] Node: %NODE_DIR%
call "%NODE_DIR%\npm.cmd" run build
if errorlevel 1 pause
endlocal
