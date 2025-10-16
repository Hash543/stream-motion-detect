#!/usr/bin/env python3
"""
Windows 系統安裝腳本
解決 dlib 編譯問題
"""

import subprocess
import sys
import platform

def install_package(package):
    """安裝單個套件"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ 成功安裝: {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 安裝失敗: {package} - {e}")
        return False

def main():
    print("=== RTSP 監控系統套件安裝腳本 ===")
    print(f"Python 版本: {sys.version}")
    print(f"作業系統: {platform.system()} {platform.release()}")
    print()

    # 基礎套件
    basic_packages = [
        "numpy==1.24.3",
        "opencv-python==4.8.1.78",
        "Pillow==10.0.1",
        "requests==2.31.0",
        "pydantic==2.4.2",
        "pydantic-settings==2.0.3",
        "python-dotenv==1.0.0",
        "aiofiles==23.2.0",
        "scipy==1.11.3",
        "imutils==0.5.4"
    ]

    # AI/ML 相關套件
    ml_packages = [
        "torch==2.1.0",
        "torchvision==0.16.0",
        "ultralytics==8.0.196",
        "mediapipe==0.10.7",
        "onnxruntime==1.16.1"
    ]

    # Web 框架
    web_packages = [
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "python-multipart==0.0.6",
        "python-jose[cryptography]==3.3.0",
        "passlib[bcrypt]==1.7.4"
    ]

    # 資料庫相關
    db_packages = [
        "sqlalchemy==2.0.23",
        "alembic==1.12.1"
    ]

    # 非同步相關
    async_packages = [
        "aiohttp",
        "asyncio-mqtt==0.16.1"
    ]

    print("1. 安裝基礎套件...")
    failed_basic = []
    for package in basic_packages:
        if not install_package(package):
            failed_basic.append(package)

    print("\n2. 安裝 AI/ML 套件...")
    failed_ml = []
    for package in ml_packages:
        if not install_package(package):
            failed_ml.append(package)

    print("\n3. 安裝 Web 框架...")
    failed_web = []
    for package in web_packages:
        if not install_package(package):
            failed_web.append(package)

    print("\n4. 安裝資料庫套件...")
    failed_db = []
    for package in db_packages:
        if not install_package(package):
            failed_db.append(package)

    print("\n5. 安裝非同步套件...")
    failed_async = []
    for package in async_packages:
        if not install_package(package):
            failed_async.append(package)

    # 處理 dlib (Windows 特殊處理)
    print("\n6. 安裝 dlib (Windows 特殊處理)...")
    dlib_success = False

    if platform.system() == "Windows":
        print("檢測到 Windows 系統，使用預編譯 wheel...")

        # 嘗試不同的 dlib 安裝方法
        dlib_methods = [
            "dlib",
            # 如果直接安裝失敗，可以嘗試從其他源安裝
        ]

        for method in dlib_methods:
            print(f"嘗試方法: {method}")
            if install_package(method):
                dlib_success = True
                break
    else:
        # Linux/Mac 系統
        dlib_success = install_package("dlib==19.24.2")

    # 安裝 face_recognition (依賴 dlib)
    print("\n7. 安裝人臉識別套件...")
    face_recognition_success = False
    if dlib_success:
        face_recognition_success = install_package("face-recognition==1.3.0")
    else:
        print("⚠ 跳過 face-recognition (dlib 安裝失敗)")

    # 安裝 insightface
    print("\n8. 安裝 InsightFace...")
    insightface_success = install_package("insightface==0.7.3")

    # 總結
    print("\n" + "="*50)
    print("安裝總結:")
    print("="*50)

    if failed_basic:
        print(f"✗ 基礎套件安裝失敗: {len(failed_basic)} 個")
        for pkg in failed_basic:
            print(f"  - {pkg}")
    else:
        print("✓ 基礎套件安裝完成")

    if failed_ml:
        print(f"✗ AI/ML套件安裝失敗: {len(failed_ml)} 個")
    else:
        print("✓ AI/ML套件安裝完成")

    if not dlib_success:
        print("✗ dlib 安裝失敗")
        print("  解決方案:")
        print("  1. 安裝 Visual Studio Build Tools")
        print("  2. 或使用 conda: conda install -c conda-forge dlib")
        print("  3. 或下載預編譯 wheel: https://github.com/z-mahmud22/Dlib_Windows_Python3.x")
    else:
        print("✓ dlib 安裝成功")

    if not face_recognition_success:
        print("✗ face-recognition 安裝失敗 (需要 dlib)")
    else:
        print("✓ face-recognition 安裝成功")

    print("\n建議:")
    if not dlib_success:
        print("- 如果 dlib 安裝失敗，可以:")
        print("  1. 只使用 MediaPipe 進行人臉檢測 (已包含)")
        print("  2. 或按照上述方案安裝 dlib")
        print("- 系統仍可正常運行其他功能")
    else:
        print("- 所有套件安裝完成，可以開始使用系統")

if __name__ == "__main__":
    main()