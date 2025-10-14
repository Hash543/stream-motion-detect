"""
Start API Service
啟動API服務
"""

import sys
import os

# 設定編碼
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("RTSP Stream Monitoring API Server")
    print("=" * 60)
    print("\nAPI Documentation: http://localhost:8282/api/docs")
    print("Health Check: http://localhost:8282/api/health")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60)

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8282,
        reload=True,
        log_level="info"
    )
