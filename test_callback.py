"""
コールバック機能のテストスクリプト
"""
import requests
import json
from flask import Flask, request as flask_request
import threading
import time

# シンプルなコールバック受信サーバー
callback_app = Flask(__name__)

received_callbacks = []

@callback_app.route('/callback', methods=['GET'])
def receive_callback():
    """コールバックを受信"""
    received_callbacks.append({
        "timestamp": time.time(),
        "url": flask_request.url
    })
    
    print("\n" + "=" * 60)
    print("📞 コールバック受信！（FAX送信成功）")
    print("=" * 60)
    print(f"URL: {flask_request.url}")
    print(f"パラメータ: なし（URLのみ）")
    print("=" * 60 + "\n")
    
    return {"status": "ok", "message": "コールバックを受信しました"}, 200

def start_callback_server():
    """コールバック受信サーバーを起動"""
    print("コールバック受信サーバーを起動中... (http://localhost:8888)")
    callback_app.run(port=8888, debug=False, use_reloader=False)

def test_callback_notification():
    """コールバック通知のテスト"""
    print("\n" + "=" * 60)
    print("コールバック機能のテスト")
    print("=" * 60)
    
    # FAX送信APIにリクエスト（コールバックURL付き）
    data = {
        "file_url": "file:///E:/DEVELOP/PYTHON/fax-auto-sender/fax_test.pdf",
        "fax_number": "0312345678",
        "request_user": "テストユーザー",
        "file_name": "テストファイル.pdf",
        "callback_url": "http://localhost:8888/callback"
    }
    
    print(f"\nFAX送信リクエストを送信中...")
    print(f"コールバックURL: {data['callback_url']}")
    
    try:
        response = requests.post('http://localhost:5000/send_fax', json=data)
        result = response.json()
        
        if result.get('success'):
            print(f"\n✅ FAX送信リクエスト登録成功")
            print(f"   ID: {result.get('request_id')}")
            print(f"\nFAX送信処理の完了を待機中...")
            print(f"（コールバックが届くまで最大60秒待ちます）")
            
            # コールバックを待機
            timeout = 60
            start_time = time.time()
            while time.time() - start_time < timeout:
                if len(received_callbacks) > 0:
                    print(f"\n✅ コールバックを受信しました！")
                    break
                time.sleep(1)
            else:
                print(f"\n⚠ タイムアウト: {timeout}秒以内にコールバックが届きませんでした")
        else:
            print(f"\n❌ FAX送信リクエスト失敗: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ エラー: {e}")

def test_callback_without_url():
    """コールバックURLなしのテスト（通常動作確認）"""
    print("\n" + "=" * 60)
    print("コールバックURLなしのテスト（通常動作）")
    print("=" * 60)
    
    data = {
        "file_url": "file:///E:/DEVELOP/PYTHON/fax-auto-sender/fax_test.pdf",
        "fax_number": "0398765432",
        "request_user": "テストユーザー2",
        "file_name": "コールバックなし.pdf"
        # callback_url は指定しない
    }
    
    print(f"\nFAX送信リクエストを送信中（コールバックURLなし）...")
    
    try:
        response = requests.post('http://localhost:5000/send_fax', json=data)
        result = response.json()
        
        if result.get('success'):
            print(f"\n✅ FAX送信リクエスト登録成功")
            print(f"   ID: {result.get('request_id')}")
            print(f"   コールバックURLは設定されていないため、通知は送信されません")
        else:
            print(f"\n❌ FAX送信リクエスト失敗: {result.get('error')}")
            
    except Exception as e:
        print(f"\n❌ エラー: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("コールバック機能テストツール")
    print("=" * 60)
    print("\n注意:")
    print("1. FAX送信APIサーバー (http://localhost:5000) が起動していることを確認してください")
    print("2. このスクリプトはコールバック受信サーバーも起動します")
    print("3. Ctrl+C で終了してください\n")
    
    # コールバック受信サーバーを別スレッドで起動
    server_thread = threading.Thread(target=start_callback_server, daemon=True)
    server_thread.start()
    
    # サーバーの起動を待機
    time.sleep(2)
    
    try:
        # テスト1: コールバック付き
        test_callback_notification()
        
        # テスト2: コールバックなし
        test_callback_without_url()
        
        # 最終結果
        print("\n" + "=" * 60)
        print("テスト完了")
        print("=" * 60)
        print(f"受信したコールバック数: {len(received_callbacks)}")
        
        if len(received_callbacks) > 0:
            print("\n受信したコールバック一覧:")
            for i, callback in enumerate(received_callbacks, 1):
                print(f"\n{i}. {callback}")
        
        print("\n管理画面で結果を確認: http://localhost:5000")
        print("\nコールバック受信サーバーは起動したままです。")
        print("終了するには Ctrl+C を押してください...")
        
        # サーバーを起動し続ける
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n終了します...")

