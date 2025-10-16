# 測試腳本 (Test Scripts)

本目錄包含各功能模組的測試腳本。

## API 測試

### `test_api.py`
**用途**: API 功能測試

**功能**:
- 測試 API 端點
- 驗證回應格式
- 檢查錯誤處理

**執行方式**:
```bash
python scripts/test/test_api.py
```

### `test_users_api.py`
**用途**: 使用者 API 測試

**功能**:
- 測試使用者註冊
- 測試使用者登入
- 測試使用者權限
- 測試 CRUD 操作

**執行方式**:
```bash
python scripts/test/test_users_api.py
```

## 資料庫測試

### `test_postgres.py`
**用途**: PostgreSQL 功能測試

**功能**:
- 測試資料庫連線
- 測試 CRUD 操作
- 驗證資料完整性

**執行方式**:
```bash
python scripts/test/test_postgres.py
```

### `test_pg_connection.py`
**用途**: PostgreSQL 連線測試

**功能**:
- 測試連線參數
- 驗證使用者權限
- 檢查資料庫狀態

**執行方式**:
```bash
python scripts/test/test_pg_connection.py
```

### `test_app_pg_connection.py`
**用途**: 應用程式資料庫連線測試

**功能**:
- 測試應用程式層的資料庫連線
- 驗證 ORM 配置
- 檢查連線池

**執行方式**:
```bash
python scripts/test/test_app_pg_connection.py
```

## 影像處理測試

### `test_streams.py`
**用途**: 影像串流測試（中文版）

**功能**:
- 測試 RTSP 串流連線
- 驗證影像擷取
- 測試串流處理

**執行方式**:
```bash
python scripts/test/test_streams.py
```

### `test_streams_en.py`
**用途**: 影像串流測試（英文版）

**功能**:
- 同 test_streams.py
- 英文輸出界面

**執行方式**:
```bash
python scripts/test/test_streams_en.py
```

## 偵測功能測試

### `test_face_detection.py`
**用途**: 人臉偵測測試

**功能**:
- 測試人臉偵測模型
- 驗證偵測準確度
- 測試效能

**執行方式**:
```bash
python scripts/test/test_face_detection.py
```

### `test_face_filing.py`
**用途**: 人臉歸檔測試

**功能**:
- 測試人臉資料儲存
- 驗證人臉特徵提取
- 測試人臉比對

**執行方式**:
```bash
python scripts/test/test_face_filing.py
```

### `test_helmet_detection_with_face.py`
**用途**: 安全帽與人臉聯合偵測測試

**功能**:
- 測試安全帽偵測
- 測試人臉偵測
- 驗證聯合判斷邏輯

**執行方式**:
```bash
python scripts/test/test_helmet_detection_with_face.py
```

### `test_helmet_interval.py`
**用途**: 安全帽間隔偵測測試

**功能**:
- 測試間隔偵測邏輯
- 驗證時間閾值
- 測試誤報過濾

**執行方式**:
```bash
python scripts/test/test_helmet_interval.py
```

### `test_inactivity_detection.py`
**用途**: 靜止偵測測試

**功能**:
- 測試靜止狀態判斷
- 驗證時間閾值
- 測試警報觸發

**執行方式**:
```bash
python scripts/test/test_inactivity_detection.py
```

## 測試指南

### 執行所有測試

```bash
# 方法1: 使用 Python 的 unittest
python -m unittest discover scripts/test

# 方法2: 逐一執行
for file in scripts/test/test_*.py; do python "$file"; done
```

### 執行特定測試

```bash
# API 測試
python scripts/test/test_api.py

# 資料庫測試
python scripts/test/test_postgres.py

# 偵測測試
python scripts/test/test_face_detection.py
```

### 測試前準備

1. **確認服務運行**:
   ```bash
   # 檢查 API 服務
   curl http://localhost:8282/api/health

   # 檢查資料庫
   python scripts/test/test_pg_connection.py
   ```

2. **設定測試資料**:
   - 確保有測試用的 RTSP 串流
   - 準備測試影像
   - 建立測試使用者

3. **環境變數**:
   - 確認 .env 設定正確
   - 測試環境與正式環境分離

## 測試資料

### 測試影片/串流

測試腳本可能需要以下測試資料:
- RTSP 串流位址
- 測試影像檔案
- 測試影片檔案

**設定範例** (.env):
```env
TEST_RTSP_URL=rtsp://test-server/stream
TEST_IMAGE_PATH=./test_data/test_image.jpg
TEST_VIDEO_PATH=./test_data/test_video.mp4
```

## 測試報告

測試執行後會產生:
- 終端輸出結果
- 測試日誌 (logs/test_*.log)
- 錯誤截圖 (screenshots/test_*)

## 常見問題

### Q: 測試連線失敗
A:
- 檢查服務是否運行
- 確認 .env 中的連線參數
- 檢查防火牆設定

### Q: 偵測測試失敗
A:
- 確認模型檔案存在
- 檢查測試影像路徑
- 驗證 GPU/CPU 設定

### Q: API 測試超時
A:
- 增加測試超時時間
- 檢查 API 服務負載
- 確認資料庫連線正常

## 持續整合 (CI)

可以將測試腳本整合到 CI/CD 流程:

```yaml
# .github/workflows/test.yml 範例
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          python scripts/test/test_api.py
          python scripts/test/test_postgres.py
```

## 效能測試

部分測試腳本包含效能指標:
- 偵測速度 (FPS)
- 回應時間 (ms)
- 資源使用率

執行效能測試時建議:
- 關閉其他應用程式
- 使用實際硬體環境
- 多次執行取平均值
