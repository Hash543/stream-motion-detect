"""
簡化版啟動腳本 - 僅用於 WEBCAM 串流測試
不載入 AI 偵測模型，減少資源消耗和潛在衝突
"""

from dotenv import load_dotenv
load_dotenv()

import uvicorn
import logging
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import cv2
import asyncio
import numpy as np

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 建立 FastAPI app
app = FastAPI(title="Webcam Stream Test")

# 簡單的攝影機管理
class SimpleWebcam:
    def __init__(self, device_index=0):
        self.device_index = device_index
        self.cap = None
        self.is_running = False

    def start(self):
        self.cap = cv2.VideoCapture(self.device_index)
        if self.cap.isOpened():
            self.is_running = True
            logger.info(f"Webcam {self.device_index} started")
            return True
        return False

    def get_frame(self):
        if not self.is_running or self.cap is None:
            return None
        ret, frame = self.cap.read()
        if ret and frame is not None:
            return frame
        return None

    def stop(self):
        if self.cap:
            self.cap.release()
        self.is_running = False

# 全域攝影機實例
webcam = SimpleWebcam(0)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting application...")
    if webcam.start():
        logger.info("Webcam initialized successfully")
    else:
        logger.error("Failed to initialize webcam")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down...")
    webcam.stop()

@app.get("/")
async def root():
    return {"message": "Webcam Stream Server", "status": "running" if webcam.is_running else "stopped"}

@app.get("/video")
async def get_video():
    """MJPEG 影片串流"""

    async def generate_frames():
        while True:
            frame = webcam.get_frame()

            if frame is None:
                # 建立錯誤幀
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, "No frame available", (100, 240),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                frame = error_frame

            # 編碼為 JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # 控制幀率 (~15 FPS)
            await asyncio.sleep(0.066)

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/status")
async def get_status():
    """取得攝影機狀態"""
    return {
        "webcam_running": webcam.is_running,
        "device_index": webcam.device_index
    }

if __name__ == "__main__":
    logger.info("Starting Webcam Stream Server...")
    logger.info("Video stream: http://localhost:8283/video")
    logger.info("Status: http://localhost:8283/status")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8283,
        log_level="info"
    )
