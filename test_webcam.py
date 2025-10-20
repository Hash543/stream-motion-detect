"""
Simple webcam test script
"""
import cv2
import time

print("Testing webcam access...")

# Try to open webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Cannot open webcam!")
    exit(1)

print("Webcam opened successfully!")
print(f"Resolution: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
print(f"FPS: {cap.get(cv2.CAP_PROP_FPS)}")

# Try to read a few frames
for i in range(5):
    ret, frame = cap.read()
    if ret and frame is not None:
        print(f"Frame {i+1}: Successfully read {frame.shape}")
    else:
        print(f"Frame {i+1}: Failed to read (ret={ret})")
    time.sleep(0.5)

cap.release()
print("Test completed!")
