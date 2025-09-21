# RTSP監控系統 - 快速開始指南

## ✅ 系統狀態

✅ **核心功能已完成**
- RTSP串流管理
- 安全帽檢測 (YOLO)
- 瞌睡檢測 (MediaPipe)
- 人臉檢測 (MediaPipe)
- 截圖管理
- API通知
- 資料庫儲存

⚠️ **已知限制**
- `dlib` 套件安裝失敗 (Windows編譯問題)
- `face_recognition` 因依賴dlib而無法使用
- 已改用 MediaPipe 作為替代方案

## 🚀 快速啟動

### 1. 依賴套件狀態
```bash
✅ OpenCV - 影像處理
✅ PyTorch + Ultralytics - YOLO安全帽檢測
✅ MediaPipe - 人臉檢測和瞌睡檢測
✅ FastAPI + SQLAlchemy - API和資料庫
✅ NumPy 1.26.4 - 數值計算
❌ dlib - 編譯失敗 (已用MediaPipe替代)
❌ face_recognition - 依賴dlib (已用MediaPipe替代)
```

### 2. 啟動系統
```bash
# 方法1: 使用簡化啟動腳本 (推薦)
python start_system.py

# 方法2: 使用原始腳本
python main.py --validate-config
```

### 3. 設定RTSP來源
編輯 `config/config.json`:
```json
{
  "rtsp_sources": [
    {
      "id": "camera_001",
      "url": "rtsp://你的攝影機IP:554/stream1",
      "location": "入口"
    }
  ]
}
```

## 🔧 解決dlib安裝問題 (可選)

如果你想使用完整的人臉識別功能:

### 方法1: 使用Conda (推薦)
```bash
conda install -c conda-forge dlib
pip install face_recognition
```

### 方法2: 下載預編譯Wheel
1. 前往: https://github.com/z-mahmud22/Dlib_Windows_Python3.x
2. 下載對應Python版本的.whl檔案
3. 安裝: `pip install dlib-19.24.2-cp311-cp311-win_amd64.whl`

### 方法3: 安裝Visual Studio Build Tools
1. 下載 Microsoft C++ Build Tools
2. 重新安裝: `pip install dlib`

## 📊 功能對照表

| 功能 | 目前狀態 | 使用技術 |
|------|----------|----------|
| RTSP串流處理 | ✅ 正常 | OpenCV |
| 安全帽檢測 | ✅ 正常 | YOLO v8 |
| 瞌睡檢測 | ✅ 正常 | MediaPipe + EAR演算法 |
| 人臉檢測 | ✅ 正常 | MediaPipe |
| 人臉識別 | ⚠️ 簡化版 | MediaPipe (無編碼特徵) |
| 截圖儲存 | ✅ 正常 | OpenCV |
| API通知 | ✅ 正常 | aiohttp |
| 資料庫 | ✅ 正常 | SQLite |

## 🔍 測試功能

### 1. 驗證設定檔
```bash
python start_system.py
# 選擇 N (不啟動監控，只驗證)
```

### 2. 測試API連接
```bash
python main.py --test-connection
```

### 3. 查看系統狀態
```bash
python main.py --status
```

## ⚡ 效能建議

1. **降低處理頻率**
   ```json
   "detection_settings": {
     "processing_fps": 1  // 從2降到1
   }
   ```

2. **使用GPU加速** (如果可用)
   - 系統會自動檢測CUDA
   - 確保安裝了對應的PyTorch CUDA版本

3. **調整信心度閾值**
   ```json
   "detection_settings": {
     "helmet_confidence_threshold": 0.8  // 提高閾值減少誤報
   }
   ```

## 🐛 常見問題

**Q: 系統啟動但沒有檢測到違規？**
A: 檢查RTSP URL是否正確，攝影機是否在線

**Q: 安全帽檢測不準確？**
A: 調整 `helmet_confidence_threshold` 或使用自訂YOLO模型

**Q: 想要更精確的人臉識別？**
A: 安裝dlib和face_recognition套件

**Q: 記憶體使用量過高？**
A: 降低processing_fps或減少同時處理的攝影機數量

## 📞 技術支援

系統基本功能已經完成並可以正常運作。如果需要：
1. 自訂AI模型訓練
2. 高精度人臉識別
3. 效能優化調整
4. 功能擴展開發

請參考完整的 README.md 或聯繫技術支援。

---
**當前版本**: v1.0 (核心功能完整)
**最後更新**: 2024-09-21