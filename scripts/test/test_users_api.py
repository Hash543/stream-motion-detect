"""
測試 Users API
"""
import requests
import json

BASE_URL = "http://localhost:8282"

def test_login():
    """測試登入"""
    print("\n=== 測試登入 ===")
    url = f"{BASE_URL}/api/auth/login"
    data = {
        "username": "superuser",
        "password": "superuser1234567",
        "remember": False
    }

    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

    if response.status_code == 200:
        result = response.json().get("result", {})
        token = result.get("access_token")
        if token:
            return token
    return None


def test_user_profile(token):
    """測試取得使用者 profile"""
    print("\n=== 測試取得使用者 profile ===")
    url = f"{BASE_URL}/api/users/profile"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_user_list(token):
    """測試取得使用者列表"""
    print("\n=== 測試取得使用者列表 ===")
    url = f"{BASE_URL}/api/users/list"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page": 1, "pageSize": 10}

    response = requests.get(url, headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_get_user_by_id(token, user_id=1):
    """測試根據 ID 取得使用者"""
    print(f"\n=== 測試根據 ID 取得使用者 (ID={user_id}) ===")
    url = f"{BASE_URL}/api/users/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_user_select_options(token):
    """測試取得使用者選項"""
    print("\n=== 測試取得使用者選項 ===")
    url = f"{BASE_URL}/api/users/getUserSelectOptions"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"opR": "in", "rIds": "1"}

    response = requests.get(url, headers=headers, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def main():
    """主測試流程"""
    print("開始測試 Users API...")

    # 登入取得 token
    token = test_login()

    if not token:
        print("\n登入失敗，無法繼續測試")
        return

    print(f"\n取得 Token: {token[:50]}...")

    # 測試其他 API
    test_user_profile(token)
    test_user_list(token)
    test_get_user_by_id(token, 1)
    test_user_select_options(token)

    print("\n\n=== 測試完成 ===")


if __name__ == "__main__":
    main()
