import asyncio
import threading
import json
import time
import cv2
import numpy as np
from typing import Dict, Any, Optional
import logging
from .base_stream import BaseStream

logger = logging.getLogger(__name__)

try:
    import websockets
    import aiortc
    from aiortc import RTCPeerConnection, RTCSessionDescription
    from aiortc.contrib.media import MediaPlayer, MediaStreamTrack
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    logger.warning("WebRTC libraries not available. Install aiortc and websockets for WebRTC support.")

class WebRTCStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        if not WEBRTC_AVAILABLE:
            raise ImportError("WebRTC support requires aiortc and websockets libraries")

        self.signaling_url = config['signaling_url']
        self.ice_servers = config.get('ice_servers', [])
        self.stream_id_remote = config.get('stream_id', 'default')

        self.pc: Optional[RTCPeerConnection] = None
        self.websocket: Optional[object] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.asyncio_thread: Optional[threading.Thread] = None

        self.video_track: Optional[object] = None
        self.current_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()

    def connect(self) -> bool:
        try:
            if self.asyncio_thread and self.asyncio_thread.is_alive():
                self._cleanup_async()

            self.asyncio_thread = threading.Thread(target=self._run_async_loop, daemon=True)
            self.asyncio_thread.start()

            time.sleep(2)

            if self.is_connected:
                self.reconnect_count = 0
                self.last_error = None
                logger.info(f"Successfully connected to WebRTC stream: {self.stream_id}")
                return True
            else:
                raise Exception("Failed to establish WebRTC connection")

        except Exception as e:
            self.last_error = str(e)
            self._handle_error(f"Failed to connect to WebRTC stream: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        self.is_connected = False
        self._cleanup_async()

    def _run_async_loop(self) -> None:
        self.event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.event_loop)

        try:
            self.event_loop.run_until_complete(self._async_connect())
        except Exception as e:
            logger.error(f"Error in WebRTC async loop: {e}")
        finally:
            self.event_loop.close()

    async def _async_connect(self) -> None:
        try:
            self.pc = RTCPeerConnection(configuration={
                "iceServers": self.ice_servers
            })

            @self.pc.on("track")
            def on_track(track):
                if track.kind == "video":
                    self.video_track = track
                    asyncio.create_task(self._process_video_track())

            @self.pc.on("connectionstatechange")
            async def on_connectionstatechange():
                if self.pc.connectionState == "connected":
                    self.is_connected = True
                elif self.pc.connectionState in ["failed", "closed"]:
                    self.is_connected = False

            self.websocket = await websockets.connect(self.signaling_url)

            await self._signaling_loop()

        except Exception as e:
            logger.error(f"WebRTC connection error: {e}")
            self.is_connected = False

    async def _signaling_loop(self) -> None:
        try:
            await self.websocket.send(json.dumps({
                "type": "join",
                "room": self.stream_id_remote
            }))

            async for message in self.websocket:
                data = json.loads(message)

                if data["type"] == "offer":
                    await self._handle_offer(data)
                elif data["type"] == "ice_candidate":
                    await self._handle_ice_candidate(data)

        except Exception as e:
            logger.error(f"Signaling error: {e}")

    async def _handle_offer(self, offer_data: Dict[str, Any]) -> None:
        try:
            offer = RTCSessionDescription(
                sdp=offer_data["sdp"],
                type=offer_data["type"]
            )

            await self.pc.setRemoteDescription(offer)

            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)

            await self.websocket.send(json.dumps({
                "type": "answer",
                "sdp": answer.sdp
            }))

        except Exception as e:
            logger.error(f"Error handling offer: {e}")

    async def _handle_ice_candidate(self, candidate_data: Dict[str, Any]) -> None:
        try:
            candidate = aiortc.RTCIceCandidate(
                candidate=candidate_data["candidate"],
                sdpMid=candidate_data.get("sdpMid"),
                sdpMLineIndex=candidate_data.get("sdpMLineIndex")
            )

            await self.pc.addIceCandidate(candidate)

        except Exception as e:
            logger.error(f"Error handling ICE candidate: {e}")

    async def _process_video_track(self) -> None:
        try:
            while self.is_running and self.video_track:
                frame = await self.video_track.recv()

                if frame:
                    img = frame.to_ndarray(format="bgr24")

                    with self.frame_lock:
                        self.current_frame = img

        except Exception as e:
            logger.error(f"Error processing video track: {e}")

    def _cleanup_async(self) -> None:
        if self.event_loop and not self.event_loop.is_closed():
            if self.pc:
                asyncio.run_coroutine_threadsafe(self.pc.close(), self.event_loop)

            if self.websocket:
                asyncio.run_coroutine_threadsafe(self.websocket.close(), self.event_loop)

            self.event_loop.call_soon_threadsafe(self.event_loop.stop)

        if self.asyncio_thread and self.asyncio_thread.is_alive():
            self.asyncio_thread.join(timeout=5)

    def _capture_loop(self) -> None:
        while self.is_running:
            try:
                if not self.is_connected:
                    if not self._reconnect():
                        break
                    continue

                with self.frame_lock:
                    if self.current_frame is not None:
                        frame = self.current_frame.copy()
                        self._put_frame(frame, {
                            'source': 'webrtc',
                            'stream_id': self.stream_id_remote
                        })

                time.sleep(1.0 / 30)

            except Exception as e:
                self._handle_error(f"Error in WebRTC capture loop: {e}")
                if not self._reconnect():
                    break

    def _reconnect(self) -> bool:
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"Max reconnection attempts reached for WebRTC {self.stream_id}")
            self.is_running = False
            return False

        self.reconnect_count += 1
        logger.info(f"Attempting to reconnect WebRTC {self.stream_id} (attempt {self.reconnect_count})")

        self.disconnect()
        time.sleep(self.reconnect_delay)

        if self.connect():
            logger.info(f"Successfully reconnected WebRTC {self.stream_id}")
            return True

        return False

class MockWebRTCStream(BaseStream):
    def __init__(self, stream_id: str, name: str, location: str, config: Dict[str, Any]):
        super().__init__(stream_id, name, location, config)

        logger.warning(f"WebRTC libraries not available, using mock stream for {stream_id}")

    def connect(self) -> bool:
        self.is_connected = True
        self.last_error = "WebRTC libraries not installed - using mock stream"
        logger.warning(f"Mock WebRTC connection for {self.stream_id}")
        return True

    def disconnect(self) -> None:
        self.is_connected = False

    def _capture_loop(self) -> None:
        frame_count = 0

        while self.is_running:
            try:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)

                cv2.putText(frame, f"Mock WebRTC Stream", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(frame, f"Frame: {frame_count}", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                cv2.putText(frame, f"Install aiortc for real WebRTC", (10, 110),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                self._put_frame(frame, {'source': 'mock_webrtc', 'frame_count': frame_count})

                frame_count += 1
                time.sleep(1.0 / 30)

            except Exception as e:
                self._handle_error(f"Error in mock WebRTC capture: {e}")
                break

def create_webrtc_stream(stream_id: str, name: str, location: str, config: Dict[str, Any]):
    if WEBRTC_AVAILABLE:
        return WebRTCStream(stream_id, name, location, config)
    else:
        return MockWebRTCStream(stream_id, name, location, config)