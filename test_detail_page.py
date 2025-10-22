"""
詳細画面機能のテストスクリプト
"""
import requests
import json
import time

API_URL = "http://localhost:5000"

def test_detail_page():
    """詳細画面のテスト"""
    print("=" * 60)
    print("詳細画面機能のテスト")
    print("=" * 60)
    
    # 1. FAX送信リクエストを作成
    print("\n1. FAX送信リクエストを作成中...")
    data = {
        "file_url": "file:///E:/DEVELOP/PYTHON/fax-auto-sender/fax_test.pdf",
        "fax_number": "0312345678",
        "request_user": "テストユーザー",
        "file_name": "テストファイル.pdf",
        "callback_url": "https://example.com/callback"
    }
    
    try:
        response = requests.post(f"{API_URL}/send_fax", json=data)
        result = response.json()
        
        if result.get('success'):
            request_id = result.get('request_id')
            print(f"✅ FAX送信リクエスト作成成功")
            print(f"   ID: {request_id}")
            
            # 2. ステータスAPIで確認
            print("\n2. ステータスAPIで確認中...")
            time.sleep(1)
            response = requests.get(f"{API_URL}/status/{request_id}")
            status_data = response.json()
            
            if status_data.get('success'):
                request = status_data['request']
                print(f"✅ ステータス取得成功")
                print(f"   ステータス: {request.get('status')}")
                print(f"   依頼者: {request.get('request_user')}")
                print(f"   ファイル名: {request.get('file_name')}")
            else:
                print(f"❌ ステータス取得失敗: {status_data.get('error')}")
            
            # 3. 詳細画面のURLを表示
            detail_url = f"{API_URL}/{request_id}"
            print(f"\n3. 詳細画面のURL:")
            print(f"   {detail_url}")
            print(f"\n   ブラウザでこのURLを開いて詳細画面を確認してください。")
            
            # 4. 詳細画面にアクセスしてHTMLを取得
            print(f"\n4. 詳細画面にアクセス中...")
            response = requests.get(detail_url)
            
            if response.status_code == 200:
                print(f"✅ 詳細画面の取得成功 (ステータスコード: {response.status_code})")
                print(f"   コンテンツタイプ: {response.headers.get('Content-Type')}")
                print(f"   コンテンツサイズ: {len(response.text)} bytes")
                
                # HTMLの内容を確認
                if "FAX送信リクエスト詳細" in response.text:
                    print(f"✅ 詳細画面のタイトルを確認")
                if "テストユーザー" in response.text:
                    print(f"✅ 依頼者名が表示されている")
                if "テストファイル.pdf" in response.text:
                    print(f"✅ ファイル名が表示されている")
                if "0312345678" in response.text:
                    print(f"✅ FAX番号が表示されている")
            else:
                print(f"❌ 詳細画面の取得失敗 (ステータスコード: {response.status_code})")
            
            # 5. 管理画面のリンク確認
            print(f"\n5. 管理画面からのリンク確認:")
            print(f"   管理画面: {API_URL}/")
            print(f"   管理画面のIDカラムをクリックすると詳細画面に遷移します")
            
        else:
            print(f"❌ FAX送信リクエスト作成失敗: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

def test_nonexistent_request():
    """存在しないリクエストIDのテスト"""
    print("\n" + "=" * 60)
    print("存在しないリクエストIDのテスト")
    print("=" * 60)
    
    fake_id = "00000000-0000-0000-0000-000000000000"
    detail_url = f"{API_URL}/{fake_id}"
    
    print(f"\n存在しないID: {fake_id}")
    print(f"URL: {detail_url}")
    
    try:
        response = requests.get(detail_url)
        
        if response.status_code == 404:
            print(f"✅ 正しく404エラーが返されました")
            print(f"   メッセージ: {response.text[:100]}")
        else:
            print(f"⚠ 予期しないステータスコード: {response.status_code}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")

def list_all_requests():
    """すべてのリクエストを一覧表示"""
    print("\n" + "=" * 60)
    print("登録されているリクエスト一覧")
    print("=" * 60)
    
    try:
        response = requests.get(f"{API_URL}/requests")
        data = response.json()
        
        if data['success']:
            print(f"\n総リクエスト数: {data['total']}")
            
            if data['total'] > 0:
                print("\n最新の5件:")
                for req in data['requests'][-5:]:
                    print(f"\n  ID: {req['id'][:8]}...")
                    print(f"  詳細画面: {API_URL}/{req['id']}")
                    print(f"  依頼者: {req.get('request_user', '-')}")
                    print(f"  ファイル名: {req.get('file_name', '-')}")
                    print(f"  ステータス: {req['status']}")
            else:
                print("\nリクエストがありません")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    print("\n詳細画面機能のテストを開始します")
    print(f"APIサーバー: {API_URL}")
    print(f"\n注意: APIサーバー ({API_URL}) が起動していることを確認してください\n")
    
    test_detail_page()
    test_nonexistent_request()
    list_all_requests()
    
    print("\n" + "=" * 60)
    print("テスト完了！")
    print("=" * 60)
    print(f"\n管理画面: {API_URL}/")
    print(f"各リクエストのIDをクリックすると詳細画面が表示されます")
    print("=" * 60)

