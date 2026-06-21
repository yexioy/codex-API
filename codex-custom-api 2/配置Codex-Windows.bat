@echo off
REM ============================================================
REM  Codex 自定义 API 一键配置 —— Windows 双击启动器
REM  把本文件和 codex-setup.py 放在同一个文件夹，双击即可。
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

REM 优先用 py 启动器，其次 python
where py >nul 2>nul
if %errorlevel%==0 (
    py "%~dp0codex-setup.py" %*
    goto end
)
where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0codex-setup.py" %*
    goto end
)

echo.
echo [x] 没检测到 Python。请先安装 Python 3：
echo     https://www.python.org/downloads/   安装时务必勾选 "Add python.exe to PATH"
echo     装好后重新双击本文件即可。
echo.

:end
echo.
pause
