@echo off
chcp 65001 >nul
title YouTube 网红曝光合作系统 - 自动重启服务

echo ================================================================================
echo                    YouTube 网红曝光合作系统 - 启动器
echo ================================================================================
echo.
echo ✓ 功能特性:
echo   - 服务崩溃后自动重启
echo   - 完整日志记录 (logs/目录)
echo   - 最大重启次数：5 次
echo.
echo 📁 日志文件位置：%cd%\logs\
echo 🌐 访问地址：http://localhost:5000
echo.
echo 按 Ctrl+C 可停止服务
echo ================================================================================
echo.

:START
python start_server.py
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ✗ 服务异常退出！错误代码：%ERRORLEVEL%
    echo ✓ 将在 3 秒后自动重启...
    timeout /t 3 /nobreak >nul
    goto START
)

echo.
echo ✓ 服务已正常停止
pause
