# PowerShell 腳本: 將 PostgreSQL bin 目錄加入系統 PATH
# 需要管理員權限執行

$postgresPath = "C:\Program Files\PostgreSQL\17\bin"

# 檢查路徑是否存在
if (-Not (Test-Path $postgresPath)) {
    Write-Host "錯誤: PostgreSQL 路徑不存在: $postgresPath" -ForegroundColor Red
    Write-Host "請檢查 PostgreSQL 安裝路徑" -ForegroundColor Yellow
    exit 1
}

# 檢查是否已在 PATH 中
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -like "*$postgresPath*") {
    Write-Host "PostgreSQL bin 目錄已經在系統 PATH 中" -ForegroundColor Green
    exit 0
}

# 詢問用戶確認
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "PostgreSQL PATH 設定工具" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "即將將以下路徑加入系統 PATH:" -ForegroundColor Yellow
Write-Host $postgresPath -ForegroundColor White
Write-Host ""
Write-Host "這將使您可以在任何地方使用 psql 命令" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "是否繼續? (Y/N)"
if ($confirmation -ne 'Y' -and $confirmation -ne 'y') {
    Write-Host "操作已取消" -ForegroundColor Yellow
    exit 0
}

try {
    # 加入 PATH (系統級別)
    $newPath = $currentPath + ";" + $postgresPath
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")

    Write-Host ""
    Write-Host "======================================" -ForegroundColor Green
    Write-Host "成功！PostgreSQL bin 已加入系統 PATH" -ForegroundColor Green
    Write-Host "======================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "重要提示:" -ForegroundColor Yellow
    Write-Host "1. 請重新開啟命令提示字元或 PowerShell" -ForegroundColor White
    Write-Host "2. 然後執行: psql --version" -ForegroundColor White
    Write-Host "3. 應該可以看到 PostgreSQL 版本資訊" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host "錯誤: 無法修改系統 PATH" -ForegroundColor Red
    Write-Host "請確認以管理員身份執行此腳本" -ForegroundColor Yellow
    Write-Host "錯誤訊息: $_" -ForegroundColor Red
    exit 1
}
