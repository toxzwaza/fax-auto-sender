"""
新しいパラメータ（request_user, file_name, callback_url）のテストスクリプト
"""
import requests
import json

API_URL = "http://localhost:5000/send_fax"

def print_response(response):
    """レスポンスを整形して表示"""
    print(f"\nステータスコード: {response.status_code}")
    result = response.json()
    print(f"レスポンス: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    if result.get('success'):
        print(f"\n✅ 生成されたID: {result.get('id')}")
        print(f"   リクエストID: {result.get('request_id')} (後方互換用)")
        if result.get('request_user'):
            print(f"   依頼者: {result.get('request_user')}")
        if result.get('file_name'):
            print(f"   ファイル名: {result.get('file_name')}")
        if result.get('callback_url'):
            print(f"   コールバックURL: {result.get('callback_url')}")

def test_with_all_parameters():
    """すべてのパラメータを指定してテスト"""
    print("=" * 60)
    print("テスト1: すべてのパラメータを指定")
    print("=" * 60)
    
    data = {
        "file_url": "file:///E:/DEVELOP/PYTHON/fax-auto-sender/fax_test.pdf",
        "fax_number": "0312345678",
        "request_user": "山田太郎",
        "file_name": "見積書_2025年10月.pdf",
        "callback_url": "https://example.com/callback"
    }
    
    print(f"送信データ: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(API_URL, json=data)
        print_response(response)
    except Exception as e:
        print(f"エラー: {e}")

def test_with_optional_parameters():
    """オプションパラメータなしでテスト"""
    print("\n" + "=" * 60)
    print("テスト2: オプションパラメータなし（必須パラメータのみ）")
    print("=" * 60)
    
    data = {
        "file_url": "file:///E:/DEVELOP/PYTHON/fax-auto-sender/fax_test.pdf",
        "fax_number": "0398765432"
    }
    
    print(f"送信データ: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(API_URL, json=data)
        print_response(response)
    except Exception as e:
        print(f"エラー: {e}")

def test_with_partial_parameters():
    """一部のオプションパラメータを指定してテスト"""
    print("\n" + "=" * 60)
    print("テスト3: 一部のオプションパラメータを指定")
    print("=" * 60)
    
    data = {
        "file_url": "file:///E:/DEVELOP/PYTHON/fax-auto-sender/fax_test.pdf",
        "fax_number": "0356781234",
        "request_user": "佐藤花子"
        # file_name と callback_url は指定しない
    }
    
    print(f"送信データ: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(API_URL, json=data)
        print_response(response)
    except Exception as e:
        print(f"エラー: {e}")

def view_requests():
    """登録されたリクエストを確認"""
    print("\n" + "=" * 60)
    print("登録されたリクエストを確認")
    print("=" * 60)
    
    try:
        response = requests.get("http://localhost:5000/requests")
        data = response.json()
        
        if data['success']:
            print(f"\n総リクエスト数: {data['total']}")
            print("\n最新の3件:")
            for req in data['requests'][-3:]:
                print(f"\n  ID: {req['id'][:8]}...")
                print(f"  依頼者: {req.get('request_user', '-')}")
                print(f"  ファイル名: {req.get('file_name', '-')}")
                print(f"  FAX番号: {req['fax_number']}")
                print(f"  コールバックURL: {'設定あり' if req.get('callback_url') else '設定なし'}")
                print(f"  ステータス: {req['status']}")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    print("新しいパラメータのテストを開始します\n")
    
    test_with_all_parameters()
    test_with_optional_parameters()
    test_with_partial_parameters()
    view_requests()
    
    print("\n" + "=" * 60)
    print("テスト完了！")
    print("管理画面で結果を確認してください: http://localhost:5000")
    print("=" * 60)
