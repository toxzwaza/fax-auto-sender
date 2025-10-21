#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAX送信APIテストスクリプト
"""

import requests
import json
import time
from datetime import datetime

# API設定
API_BASE_URL = "http://localhost:5000"
SEND_FAX_ENDPOINT = f"{API_BASE_URL}/send_fax"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

def test_health_check():
    """ヘルスチェックテスト"""
    print("=== ヘルスチェックテスト ===")
    try:
        response = requests.get(HEALTH_ENDPOINT)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"エラー: {e}")
        return False

def test_send_fax(file_url, fax_number):
    """FAX送信テスト（非同期）"""
    print(f"\n=== FAX送信テスト ===")
    print(f"ファイルURL: {file_url}")
    print(f"FAX番号: {fax_number}")
    
    payload = {
        "file_url": file_url,
        "fax_number": fax_number
    }
    
    try:
        print("リクエスト送信中...")
        response = requests.post(
            SEND_FAX_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10  # 10秒タイムアウト（登録のみなので短縮）
        )
        
        print(f"ステータスコード: {response.status_code}")
        response_data = response.json()
        print(f"レスポンス: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200 and response_data.get('success'):
            request_id = response_data.get('request_id')
            print(f"リクエストID: {request_id}")
            
            # ステータスを確認（最大30秒待機）
            print("FAX送信の完了を待機中...")
            for i in range(30):
                time.sleep(1)
                status_response = requests.get(f"{API_BASE_URL}/status/{request_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('success'):
                        request_info = status_data.get('request', {})
                        status = request_info.get('status')
                        if status == 1:  # 完了
                            print("✅ FAX送信が完了しました")
                            return True
                        elif status == -1:  # エラー
                            print(f"❌ FAX送信に失敗しました: {request_info.get('error_message')}")
                            return False
                        else:  # まだ処理中
                            print(f"処理中... (ステータス: {status})")
            
            print("⚠ タイムアウト: FAX送信の完了を確認できませんでした")
            return False
        
        return False
        
    except requests.exceptions.Timeout:
        print("タイムアウト: リクエスト登録に時間がかかりすぎています")
        return False
    except Exception as e:
        print(f"エラー: {e}")
        return False

def test_invalid_parameters():
    """無効なパラメータテスト"""
    print(f"\n=== 無効なパラメータテスト ===")
    
    # パラメータ不足テスト
    print("1. パラメータ不足テスト")
    payload = {"file_url": "https://example.com/test.pdf"}
    
    try:
        response = requests.post(SEND_FAX_ENDPOINT, json=payload)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.json()}")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 空のパラメータテスト
    print("\n2. 空のパラメータテスト")
    payload = {"file_url": "", "fax_number": ""}
    
    try:
        response = requests.post(SEND_FAX_ENDPOINT, json=payload)
        print(f"ステータスコード: {response.status_code}")
        print(f"レスポンス: {response.json()}")
    except Exception as e:
        print(f"エラー: {e}")

def test_get_all_requests():
    """すべてのリクエストを取得するテスト"""
    print("\n=== すべてのリクエスト取得テスト ===")
    try:
        response = requests.get(f"{API_BASE_URL}/requests")
        print(f"ステータスコード: {response.status_code}")
        response_data = response.json()
        print(f"総リクエスト数: {response_data.get('total', 0)}")
        
        requests_list = response_data.get('requests', [])
        for req in requests_list[-3:]:  # 最新3件を表示
            print(f"ID: {req['id'][:8]}..., ステータス: {req['status']}, FAX番号: {req['fax_number']}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"エラー: {e}")
        return False

def main():
    """メイン関数"""
    print("FAX送信APIテストスクリプト（非同期版）")
    print("=" * 50)
    
    # ヘルスチェック
    if not test_health_check():
        print("❌ サーバーが起動していません。app.pyを起動してください。")
        return
    
    print("✅ サーバーは正常に動作しています")
    
    # テストケース1: 実際のPDFファイル（ローカルファイル）
    print("\n" + "=" * 50)
    print("テストケース1: ローカルPDFファイル")
    test_send_fax("file:///D:/PYTHON/fax_driver_test/fax_test.pdf", "0432119261")
    
    # テストケース1.5: 存在しないローカルファイル
    print("\n" + "=" * 50)
    print("テストケース1.5: 存在しないローカルファイル")
    test_send_fax("file:///D:/PYTHON/fax_driver_test/nonexistent.pdf", "0432119261")
    
    # テストケース2: オンラインPDFファイル
    print("\n" + "=" * 50)
    print("テストケース2: オンラインPDFファイル")
    test_send_fax("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf", "0432119261")
    
    # テストケース3: 無効なパラメータ
    print("\n" + "=" * 50)
    test_invalid_parameters()
    
    # テストケース4: すべてのリクエスト取得
    print("\n" + "=" * 50)
    test_get_all_requests()
    
    print("\n" + "=" * 50)
    print("テスト完了")

if __name__ == "__main__":
    main()
