# RTSP影像監控系統 - 文件目錄

本目錄包含RTSP影像監控系統的完整技術文件。

## 📚 文件列表

### [安裝指南](installation.md)
系統安裝的完整步驟，包括：
- 系統需求
- 安裝步驟
- 套件安裝
- 常見問題解決
- GPU加速設定

**適合對象**：首次安裝系統的使用者

---

### [使用指南](usage.md)
系統使用的詳細說明，包括：
- 快速開始
- 系統配置
- RTSP攝影機設定
- 多種串流格式支援
- 人臉識別管理
- 違規記錄管理
- 監控與維護
- API通知格式

**適合對象**：日常使用系統的操作人員

---

### [部署指南](deployment.md)
系統建置與部署的完整流程，包括：
- 專案架構
- 開發環境建置
- 測試流程
- 建置流程
- 多種部署方式（直接部署、Docker、Kubernetes）
- 環境配置
- 監控與維護
- 備份與恢復

**適合對象**：系統管理員、DevOps工程師

---

### [開發指南](development.md)
擴充功能開發的詳細說明，包括：
- 系統架構概述
- 開發環境設定
- 擴充新功能
  - 添加新的檢測功能
  - 添加新的串流格式
  - 添加新的通知方式
- 資料庫擴充
- API開發
- 測試開發
- 效能優化
- 最佳實踐

**適合對象**：開發人員

---

## 🚀 快速導航

### 我是新手，要如何開始？
1. 先閱讀 [安裝指南](installation.md)
2. 然後參考 [使用指南](usage.md) 的快速開始章節

### 我想部署到生產環境
1. 閱讀 [部署指南](deployment.md)
2. 參考適合你環境的部署方式
3. 配置監控與備份

### 我想開發新功能
1. 閱讀 [開發指南](development.md)
2. 設定開發環境
3. 參考範例程式碼

### 我遇到問題了
1. 查看各文件中的「故障排除」章節
2. 參考 [使用指南](usage.md) 中的常見問題
3. 查看專案 GitHub Issues

## 📖 其他資源

### 專案根目錄文件
- [README.md](../README.md) - 專案主要說明文件
- [README_快速開始.md](../README_快速開始.md) - 快速入門指南
- [README_多格式串流支援.md](../README_多格式串流支援.md) - 多格式串流說明
- [appSpec.md](../appSpec.md) - 系統開發規格書

### 設定檔範例
- `config/config.json` - 主要系統設定
- `streamSource.json` - 串流來源設定

### 測試腳本
- `test_streams.py` - 串流測試
- `test_face_detection.py` - 人臉檢測測試
- `test_helmet_interval.py` - 安全帽檢測測試
- `test_face_filing.py` - 人臉歸檔測試

## 🔧 技術棧

### 核心技術
- **Python 3.8+**
- **OpenCV** - 影像處理
- **PyTorch** - AI框架
- **Ultralytics YOLO** - 物件檢測
- **MediaPipe** - 人臉檢測
- **FastAPI** - Web框架（可選）
- **SQLAlchemy** - 資料庫ORM
- **SQLite** - 資料庫

### 支援的串流格式
- RTSP - Real Time Streaming Protocol
- WEBCAM - 本地攝影機
- HTTP_MJPEG - HTTP Motion JPEG
- HLS - HTTP Live Streaming
- DASH - Dynamic Adaptive Streaming
- WebRTC - Web Real-Time Communication
- ONVIF - 開放網路影像介面

## 🎯 主要功能

- ✅ 多攝影機RTSP串流處理
- ✅ 安全帽檢測（YOLO）
- ✅ 瞌睡檢測（EAR演算法）
- ✅ 人臉檢測與識別
- ✅ 自動截圖與標註
- ✅ RESTful API通知
- ✅ SQLite資料庫儲存
- ✅ 多格式串流支援
- ✅ 自動重連機制
- ✅ 詳細日誌記錄

## 📞 技術支援

### 遇到問題？
1. 檢查相關文件的故障排除章節
2. 查看 GitHub Issues
3. 提交新的 Issue
4. 聯絡開發團隊

### 想要貢獻？
歡迎提交Pull Request！請先閱讀 [開發指南](development.md) 中的貢獻指南。

## 📝 文件版本

- **版本**: 1.0.0
- **最後更新**: 2024-10
- **維護者**: 開發團隊

## 📄 授權

本專案採用 MIT 授權條款，詳見專案根目錄的 LICENSE 檔案。

---

**注意**: 本文件持續更新中，如發現任何錯誤或需要補充的內容，歡迎提交Issue或Pull Request。
