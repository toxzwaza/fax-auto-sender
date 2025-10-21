#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡単なFAX送信APIテストスクリプト（繰り返し実行版）
"""

import requests
import json
import time
import os

def check_file_exists(file_url):
    """ファイルの存在をチェック"""
    if file_url.startswith('file://'):
        # ローカルファイルの場合
        local_path = file_url[7:]  # file://を除去
        if local_path.startswith('/'):
            local_path = local_path[1:]  # Windowsのパス調整
        
        if os.path.exists(local_path):
            print(f"✅ ファイルが存在します: {local_path}")
            return True
        else:
            print(f"❌ ファイルが見つかりません: {local_path}")
            return False
    else:
        # リモートファイルの場合は存在チェックをスキップ
        print(f"🌐 リモートファイル: {file_url}")
        return True

def send_fax_simple(file_url, fax_number):
    """簡単なFAX送信"""
    # ファイル存在チェック
    if not check_file_exists(file_url):
        return False
    
    url = "http://monokanri-manage.local:5000/send_fax"
    
    data = {
        "file_url": file_url,
        "fax_number": fax_number
    }
    
    try:
        print(f"FAX送信開始...")
        print(f"ファイル: {file_url}")
        print(f"FAX番号: {fax_number}")
        
        response = requests.post(url, json=data)
        
        print(f"\n結果:")
        print(f"ステータス: {response.status_code}")
        print(f"レスポンス: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"エラー: {e}")
        return False

def test_remote_file_multiple():
    """リモートファイルの複数回実行テスト"""
    # リモートファイルURL
    remote_file_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    
    fax_number = "0432119261"
    repeat_count = 3  # 繰り返し回数
    interval_seconds = 2  # 実行間隔（秒）
    
    print("リモートファイルFAX送信テスト（複数回実行）")
    print("=" * 50)
    print(f"ファイルURL: {remote_file_url}")
    print(f"FAX番号: {fax_number}")
    print(f"繰り返し回数: {repeat_count}")
    print(f"実行間隔: {interval_seconds}秒")
    print("=" * 50)
    
    success_count = 0
    failure_count = 0
    
    for i in range(repeat_count):
        print(f"\n【実行 {i+1}/{repeat_count}】")
        print("-" * 30)
        print(f"ファイル: {remote_file_url}")
        
        success = send_fax_simple(remote_file_url, fax_number)
        
        if success:
            print("✅ FAX送信リクエストが登録されました")
            success_count += 1
        else:
            print("❌ FAX送信リクエストの登録に失敗しました")
            failure_count += 1
        
        # 最後の実行以外は間隔を空ける
        if i < repeat_count - 1:
            print(f"\n{interval_seconds}秒待機中...")
            time.sleep(interval_seconds)
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("実行結果サマリー")
    print("=" * 50)
    print(f"総実行回数: {repeat_count}")
    print(f"成功: {success_count}")
    print(f"失敗: {failure_count}")
    print(f"成功率: {(success_count/repeat_count)*100:.1f}%")

if __name__ == "__main__":
    # 設定
    remote_file_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"  # リモートファイル
    fax_number = "0432119261"  # FAX番号
    repeat_count = 0  # 繰り返し回数
    interval_seconds = 2  # 実行間隔（秒）
    
    # 実行モード選択
    mode = "single"  # "single" または "remote_multiple"

    if mode == "single":
        print("リモートファイルFAX送信テスト（単一実行）")
        print("=" * 50)
        print(f"ファイルURL: {remote_file_url}")
        print(f"FAX番号: {fax_number}")
        print("=" * 50)
        
        success = send_fax_simple(remote_file_url, fax_number)
        
        if success:
            print("✅ FAX送信リクエストが登録されました")
        else:
            print("❌ FAX送信リクエストの登録に失敗しました")
            
        time.sleep(2)
        
        success = send_fax_simple(remote_file_url, fax_number)
        
        if success:
            print("✅ FAX送信リクエストが登録されました")
        else:
            print("❌ FAX送信リクエストの登録に失敗しました")
    
    else:
        # リモートファイルの複数回実行テスト
        test_remote_file_multiple()
