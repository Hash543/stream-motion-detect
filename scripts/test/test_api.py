"""
Test API Endpoints
測試API端點
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """測試健康檢查"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_info():
    """測試系統資訊"""
    print("\n=== Testing System Info ===")
    response = requests.get(f"{BASE_URL}/api/info")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200


def test_create_person():
    """測試建立人員"""
    print("\n=== Testing Create Person ===")
    data = {
        "person_id": "test_001",
        "name": "測試人員",
        "department": "測試部門",
        "position": "測試員",
        "status": "active"
    }
    response = requests.post(f"{BASE_URL}/api/persons", json=data)
    print(f"Status Code: {response.status_code}")
    if response.status_code in [200, 201, 400]:  # 400 if already exists
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code in [200, 201, 400]


def test_list_persons():
    """測試查詢人員列表"""
    print("\n=== Testing List Persons ===")
    response = requests.get(f"{BASE_URL}/api/persons")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Found {len(data)} persons")
    if data:
        print(f"First person: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_create_stream():
    """測試建立影像來源"""
    print("\n=== Testing Create Stream Source ===")
    data = {
        "stream_id": "test_cam_001",
        "name": "測試攝影機",
        "stream_type": "RTSP",
        "url": "rtsp://192.168.1.100:554/stream1",
        "location": "測試位置",
        "enabled": True
    }
    response = requests.post(f"{BASE_URL}/api/streams", json=data)
    print(f"Status Code: {response.status_code}")
    if response.status_code in [200, 201, 400]:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code in [200, 201, 400]


def test_list_streams():
    """測試查詢影像來源列表"""
    print("\n=== Testing List Stream Sources ===")
    response = requests.get(f"{BASE_URL}/api/streams")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Found {len(data)} streams")
    if data:
        print(f"First stream: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_create_rule():
    """測試建立規則"""
    print("\n=== Testing Create Detection Rule ===")
    data = {
        "rule_id": "test_rule_001",
        "name": "測試規則",
        "description": "這是一個測試規則",
        "enabled": True,
        "detection_types": ["helmet"],
        "confidence_threshold": 0.75,
        "notification_enabled": True,
        "priority": 10
    }
    response = requests.post(f"{BASE_URL}/api/rules", json=data)
    print(f"Status Code: {response.status_code}")
    if response.status_code in [200, 201, 400]:
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    return response.status_code in [200, 201, 400]


def test_list_rules():
    """測試查詢規則列表"""
    print("\n=== Testing List Detection Rules ===")
    response = requests.get(f"{BASE_URL}/api/rules")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Found {len(data)} rules")
    if data:
        print(f"First rule: {json.dumps(data[0], indent=2, ensure_ascii=False)}")
    return response.status_code == 200


def test_rule_templates():
    """測試規則範本"""
    print("\n=== Testing Rule Templates ===")
    response = requests.get(f"{BASE_URL}/api/rules/templates/list")
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Available templates: {len(data['templates'])}")
    for template in data['templates']:
        print(f"  - {template['template_id']}: {template['name']}")
    return response.status_code == 200


def main():
    """執行所有測試"""
    print("=" * 60)
    print("RTSP Stream Monitoring API - Test Suite")
    print("=" * 60)

    tests = [
        ("Health Check", test_health),
        ("System Info", test_info),
        ("Create Person", test_create_person),
        ("List Persons", test_list_persons),
        ("Create Stream", test_create_stream),
        ("List Streams", test_list_streams),
        ("Create Rule", test_create_rule),
        ("List Rules", test_list_rules),
        ("Rule Templates", test_rule_templates),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n[ERROR] {name} failed: {e}")
            results.append((name, False))

    # 顯示結果
    print("\n" + "=" * 60)
    print("Test Results")
    print("=" * 60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
