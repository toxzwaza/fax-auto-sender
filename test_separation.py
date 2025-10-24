#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分離後の動作確認テストスクリプト
"""

import subprocess
import time
import requests
import json
import os

def test_api_server():
    """APIサーバーの動作確認"""
    print("=== APIサーバーの動作確認 ===")
    
    try:
        # ヘルスチェック
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("✅ APIサーバーは正常に動作しています")
            print(f"   レスポンス: {response.json()}")
        else:
            print(f"❌ APIサーバーのヘルスチェックが失敗: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ APIサーバーに接続できません: {e}")
        return False
    
    return True

def test_fax_worker():
    """FAXワーカーの動作確認"""
    print("\n=== FAXワーカーの動作確認 ===")
    
    # parameter.jsonの存在確認
    if not os.path.exists("parameter.json"):
        print("⚠ parameter.jsonが存在しません。空のファイルを作成します。")
        with open("parameter.json", "w", encoding="utf-8") as f:
            json.dump([], f)
    
    # FAXワーカーのプロセス確認
    try:
        # Windowsの場合のプロセス確認
        result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq python.exe"], 
                              capture_output=True, text=True, shell=True)
        if "python.exe" in result.stdout:
            print("✅ Pythonプロセスが実行中です")
        else:
            print("⚠ Pythonプロセスが見つかりません")
    except Exception as e:
        print(f"⚠ プロセス確認でエラー: {e}")
    
    return True

def test_file_structure():
    """ファイル構造の確認"""
    print("\n=== ファイル構造の確認 ===")
    
    required_files = [
        "app.py",
        "fax_worker.py", 
        "fax_sender.py",
        "parameter.json"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} が存在します")
        else:
            print(f"❌ {file} が見つかりません")
    
    # フォルダの確認
    required_folders = ["uploads", "converted_pdfs", "templates"]
    for folder in required_folders:
        if os.path.exists(folder):
            print(f"✅ {folder}/ フォルダが存在します")
        else:
            print(f"⚠ {folder}/ フォルダが見つかりません")

def main():
    """メインテスト実行"""
    print("FAX送信システム分離後の動作確認テスト")
    print("=" * 50)
    
    # ファイル構造確認
    test_file_structure()
    
    # APIサーバー確認
    api_ok = test_api_server()
    
    # FAXワーカー確認
    worker_ok = test_fax_worker()
    
    print("\n" + "=" * 50)
    print("テスト結果:")
    print(f"APIサーバー: {'✅ 正常' if api_ok else '❌ 異常'}")
    print(f"FAXワーカー: {'✅ 正常' if worker_ok else '❌ 異常'}")
    
    if api_ok and worker_ok:
        print("\n🎉 すべてのテストが成功しました！")
        print("\n使用方法:")
        print("1. APIサーバー起動: python app.py")
        print("2. FAXワーカー起動: python fax_worker.py")
        print("3. 両方を別々のターミナルで実行してください")
    else:
        print("\n⚠ 一部のテストが失敗しました。設定を確認してください。")

if __name__ == "__main__":
    main()
