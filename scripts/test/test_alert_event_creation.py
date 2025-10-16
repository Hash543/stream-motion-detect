"""
測試 Alert Event 建立功能
"""

import requests
import json
from datetime import datetime

# API 基礎 URL
API_BASE_URL = "http://localhost:8282"

def test_create_alert_event_basic():
    """測試基本的 alert event 建立"""
    print("\n=== 測試 1: 基本 Alert Event 建立 ===")

    event_data = {
        "camera_id": "CAM001",
        "code": 85,  # 信心度 85%
        "type": 1,   # 1: 安全帽違規
        "length": 120,
        "area": 450,
        "time": "2025-10-16 17:30:00",
        "severity": "高等",
        "image": "./screenshots/test_violation.jpg"
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/alertEvent/add",
            json=event_data,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        if response.status_code == 200:
            print("✓ 基本建立成功")
            return True
        else:
            print("✗ 基本建立失敗")
            return False

    except Exception as e:
        print(f"✗ 錯誤: {e}")
        return False


def test_create_alert_event_with_assignment():
    """測試帶自動分配的 alert event 建立"""
    print("\n=== 測試 2: 帶自動分配的 Alert Event 建立 ===")

    event_data = {
        "camera_id": "CAM002",
        "code": 90,
        "type": 7,   # 7: 靜止偵測
        "length": 150,
        "area": 600,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "severity": "中等",
        "image": "./screenshots/test_inactivity.jpg",
        "lat": 25.0330,
        "lng": 121.5654,
        "address": "",  # 空字串測試自動解析地址功能
        # 分配資訊
        "uIds": [5, 11, 12],
        "oIds": [6, 7],
        "report_status": 2  # 2: 處理中
    }

    try:
        response = requests.post(
            f"{API_BASE_URL}/api/alertEvent/add",
            json=event_data,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        if response.status_code == 200:
            print("✓ 帶分配建立成功")
            return response.json()["data"]["id"]
        else:
            print("✗ 帶分配建立失敗")
            return None

    except Exception as e:
        print(f"✗ 錯誤: {e}")
        return None


def test_search_alert_events():
    """測試搜尋 alert events (新格式)"""
    print("\n=== 測試 3: 搜尋 Alert Events (新格式) ===")

    try:
        response = requests.get(
            f"{API_BASE_URL}/api/alertEvent/search",
            params={"page": 1, "pageSize": 10}
        )

        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Response 結構: {json.dumps(result, indent=2, ensure_ascii=False, default=str)}")

        if response.status_code == 200:
            # 檢查新格式
            assert "status" in result, "缺少 status 欄位"
            assert result["status"] == "success", "status 不是 success"
            assert "data" in result, "缺少 data 欄位"
            assert "msg" in result["data"], "缺少 msg 欄位"
            assert "list" in result["data"], "缺少 list 欄位"

            print(f"✓ 搜尋成功，格式正確")
            print(f"  找到 {len(result['data']['list'])} 筆記錄")
            return True
        else:
            print("✗ 搜尋失敗")
            return False

    except Exception as e:
        print(f"✗ 錯誤: {e}")
        return False


def test_violations_list_format():
    """測試 violations API 列表格式"""
    print("\n=== 測試 4: Violations API 列表格式 ===")

    try:
        response = requests.get(f"{API_BASE_URL}/api/violations/")

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Response 結構: {json.dumps(result, indent=2, ensure_ascii=False, default=str)}")

            # 檢查新格式
            assert "status" in result, "缺少 status 欄位"
            assert result["status"] == "success", "status 不是 success"
            assert "data" in result, "缺少 data 欄位"
            assert "msg" in result["data"], "缺少 msg 欄位"
            assert "list" in result["data"], "缺少 list 欄位"

            print(f"✓ Violations 列表格式正確")
            print(f"  找到 {len(result['data']['list'])} 筆記錄")
            return True
        else:
            print("✗ Violations 列表格式檢查失敗")
            return False

    except Exception as e:
        print(f"✗ 錯誤: {e}")
        return False


def main():
    """主測試函數"""
    print("="*60)
    print("Alert Event 功能測試")
    print("="*60)

    results = []

    # 測試 1: 基本建立
    results.append(("基本建立", test_create_alert_event_basic()))

    # 測試 2: 帶分配建立
    event_id = test_create_alert_event_with_assignment()
    results.append(("帶分配建立", event_id is not None))

    # 測試 3: 搜尋新格式
    results.append(("搜尋新格式", test_search_alert_events()))

    # 測試 4: Violations 列表格式
    results.append(("Violations 列表格式", test_violations_list_format()))

    # 總結
    print("\n" + "="*60)
    print("測試總結")
    print("="*60)

    for test_name, result in results:
        status = "✓ 通過" if result else "✗ 失敗"
        print(f"{test_name:20s}: {status}")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n總計: {passed}/{total} 測試通過")

    if passed == total:
        print("\n所有測試通過！")
        return 0
    else:
        print(f"\n有 {total - passed} 個測試失敗")
        return 1


if __name__ == "__main__":
    exit(main())
