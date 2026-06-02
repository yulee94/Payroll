@echo off
chcp 65001 >nul
setlocal
set "SRC=%~dp0.."
set "DATA_DIR=%LOCALAPPDATA%\Bitween\Payroll"

echo Bitween 로그인 계정 복구
if not exist "%DATA_DIR%\users" mkdir "%DATA_DIR%\users"
copy /Y "%SRC%\users\registry.json" "%DATA_DIR%\users\" >nul
copy /Y "%SRC%\tenants.json" "%DATA_DIR%\" >nul
echo 완료: %DATA_DIR%
pause
