@echo off
chcp 65001 >nul 2>&1

:: ============================================
::  SenseType - 本地语音输入
::  双击启动，自动请求管理员权限
:: ============================================

:: 检查是否已有管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    :: 没有管理员权限，用 PowerShell 重新以管理员身份启动
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

:: 切换到脚本所在目录（项目根目录）
cd /d "%~dp0"

:: Python 路径（winvoice 环境）
set "PYTHON=%USERPROFILE%\micromamba\envs\winvoice\python.exe"

:: 检查 Python 是否存在
if not exist "%PYTHON%" (
    echo.
    echo  [ERROR] Python not found: %PYTHON%
    echo.
    echo  Please install the winvoice environment first.
    echo  See: Windows平台部署指南.md
    echo.
    pause
    exit /b 1
)

:: 启动 SenseType
echo  Starting SenseType...
echo.
"%PYTHON%" -m sensetype

:: 如果异常退出，暂停显示错误
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] SenseType exited with error code: %errorlevel%
    echo.
    pause
)
