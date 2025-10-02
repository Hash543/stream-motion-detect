# 安裝指南

## 系統需求

### 硬體需求
- **CPU**: 多核心處理器（建議8核心以上）
- **記憶體**: 16GB RAM 以上
- **GPU**: NVIDIA GPU（建議，用於AI加速）
- **儲存空間**: 500GB+ SSD（用於截圖與日誌）
- **網路**: 千兆網路（支援多個RTSP串流）

### 軟體需求
- **作業系統**: Windows 10+, Ubuntu 20.04+, macOS 10.15+
- **Python**: 3.8 或更高版本
- **Git**: 用於版本控制（可選）

## 安裝步驟

### 1. 安裝Python

確認Python版本：
```bash
python --version
```

如果未安裝Python 3.8+，請前往 [python.org](https://www.python.org/downloads/) 下載安裝。

### 2. 下載專案

#### 方法1: 使用Git（推薦）
```bash
git clone https://github.com/your-repo/stream-motion-detect.git
cd stream-motion-detect
```

#### 方法2: 下載ZIP
從專案頁面下載ZIP檔案並解壓縮。

### 3. 建立虛擬環境（建議）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python -m venv venv
source venv/bin/activate
```

### 4. 安裝Python套件

#### 基本安裝
```bash
pip install -r requirements.txt
```

#### 最小化安裝（僅核心功能）
```bash
pip install -r requirements_minimal.txt
```

#### 完整串流支援安裝
```bash
pip install -r requirements_streaming.txt
```

### 5. 套件安裝狀態

安裝完成後，核心套件包括：
- ✅ **OpenCV** 4.8.1+ - 影像處理
- ✅ **PyTorch** 2.1.0+ - AI框架
- ✅ **Ultralytics** 8.0.196+ - YOLO模型
- ✅ **MediaPipe** 0.10.7+ - 人臉檢測
- ✅ **FastAPI** 0.104.1+ - Web框架
- ✅ **SQLAlchemy** 2.0.23+ - 資料庫ORM
- ✅ **NumPy** 1.26.4 - 數值計算

### 6. 解決常見安裝問題

#### dlib 安裝失敗（Windows）

**方法1: 使用Conda（推薦）**
```bash
conda install -c conda-forge dlib
pip install face_recognition
```

**方法2: 下載預編譯Wheel**
1. 前往 [dlib預編譯檔案](https://github.com/z-mahmud22/Dlib_Windows_Python3.x)
2. 下載對應Python版本的.whl檔案
3. 安裝：
```bash
pip install dlib-19.24.2-cp311-cp311-win_amd64.whl
```

**方法3: 使用替代方案**
系統已內建MediaPipe作為替代方案，可直接使用而不需要dlib。

#### PyTorch CUDA支援

如需GPU加速，請安裝對應的CUDA版本：

```bash
# CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

驗證CUDA是否可用：
```bash
python -c "import torch; print(torch.cuda.is_available())"
```

### 7. 下載AI模型（可選）

系統會在首次執行時自動下載所需模型，或手動下載：

```bash
# YOLO模型
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt -O yolov8n.pt

# 自訂安全帽檢測模型（如有）
# 放置於 models/helmet_detection.pt
```

### 8. 初始化資料庫與目錄

系統會在首次啟動時自動建立所需目錄：
- `screenshots/` - 截圖儲存
- `logs/` - 日誌檔案
- `data/` - 資料庫檔案

也可以手動建立：
```bash
mkdir screenshots logs data
```

### 9. 設定系統配置

複製並編輯設定檔：
```bash
# 複製範例設定
cp config/config.json.example config/config.json

# 編輯設定
# Windows: notepad config/config.json
# Linux/macOS: nano config/config.json
```

基本設定項目：
```json
{
  "rtsp_sources": [
    {
      "id": "camera_001",
      "url": "rtsp://您的攝影機IP:554/stream1",
      "location": "入口"
    }
  ],
  "notification_api": {
    "endpoint": "https://您的伺服器.com/api/violations"
  }
}
```

### 10. 驗證安裝

執行系統驗證腳本：
```bash
python start_system.py
```

或使用驗證命令：
```bash
python main.py --validate-config
```

成功訊息範例：
```
✅ 設定檔載入成功
✅ AI模型載入成功
✅ 資料庫連接成功
✅ 系統準備就緒
```

## 進階安裝選項

### Docker安裝（開發中）

```bash
# 建置Docker映像
docker build -t stream-motion-detect .

# 執行容器
docker run -d \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/screenshots:/app/screenshots \
  -p 8000:8000 \
  stream-motion-detect
```

### 額外功能套件

#### HLS串流支援
```bash
pip install m3u8
```

#### WebRTC串流支援
```bash
pip install aiortc websockets
```

#### ONVIF串流支援
```bash
pip install onvif-zeep
```

## 故障排除

### 套件衝突

如遇到套件版本衝突：
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### 權限問題（Linux/macOS）

```bash
sudo chmod +x start_system.py
sudo chown -R $USER:$USER screenshots/ logs/ data/
```

### 記憶體不足

調整處理設定以降低記憶體使用：
```json
{
  "detection_settings": {
    "processing_fps": 1
  }
}
```

## 下一步

安裝完成後，請參考：
- [使用指南](usage.md) - 了解如何使用系統
- [配置說明](configuration.md) - 詳細的配置選項
- [故障排除](troubleshooting.md) - 常見問題解決

## 技術支援

如安裝過程遇到問題：
1. 檢查 [常見問題](troubleshooting.md)
2. 查看 [GitHub Issues](https://github.com/your-repo/stream-motion-detect/issues)
3. 聯絡技術支援團隊
