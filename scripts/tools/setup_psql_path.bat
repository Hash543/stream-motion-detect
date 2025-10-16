@echo off
REM 批次檔: 將 PostgreSQL bin 目錄加入系統 PATH
REM 需要管理員權限執行

echo ======================================
echo PostgreSQL PATH 設定工具
echo ======================================
echo.
echo 此腳本將設定 PostgreSQL 的 psql 命令
echo 需要管理員權限執行
echo.

REM 檢查管理員權限
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo 錯誤: 需要管理員權限
    echo 請右鍵點擊此檔案，選擇「以系統管理員身分執行」
    pause
    exit /b 1
)

set POSTGRES_BIN=C:\Program Files\PostgreSQL\17\bin

REM 檢查路徑是否存在
if not exist "%POSTGRES_BIN%\psql.exe" (
    echo 錯誤: 找不到 psql.exe
    echo 路徑: %POSTGRES_BIN%
    pause
    exit /b 1
)

echo 將要加入的路徑: %POSTGRES_BIN%
echo.
echo 按任意鍵繼續，或關閉視窗取消...
pause > nul

REM 加入 PATH
setx /M PATH "%PATH%;%POSTGRES_BIN%"

if %errorLevel% equ 0 (
    echo.
    echo ======================================
    echo 成功！PostgreSQL bin 已加入系統 PATH
    echo ======================================
    echo.
    echo 重要提示:
    echo 1. 請重新開啟命令提示字元
    echo 2. 執行: psql --version
    echo 3. 應該可以看到 PostgreSQL 版本資訊
    echo.
) else (
    echo.
    echo 錯誤: 無法修改系統 PATH
    echo 請確認以管理員身份執行此腳本
    echo.
)

pause
