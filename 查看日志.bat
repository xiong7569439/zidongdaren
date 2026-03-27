@echo off
chcp 65001 >nul
title 服务日志查看器

echo ================================================================================
echo                         服务日志实时监控
echo ================================================================================
echo.
echo 📁 日志目录：%cd%\logs\
echo.
echo 正在加载最新的日志文件...
echo.

:: 查找最新的日志文件
for /f "delims=" %%i in ('dir /b /o-d logs\web_server_*.log 2^>nul') do (
    set "LATEST_LOG=%%i"
    goto :SHOW_LOG
)

echo ✗ 未找到日志文件，请先启动服务
pause
exit /b

:SHOW_LOG
echo ✓ 找到最新日志：logs\%LATEST_LOG%
echo.
echo 按 Ctrl+C 停止监控
echo ================================================================================
echo.

:: 实时显示日志内容
tail -f logs\%LATEST_LOG%
