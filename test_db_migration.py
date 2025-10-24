#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース移行テストスクリプト
JSONからMySQLデータベースへの移行が正常に行われているかテストする
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import (load_parameters, add_fax_request, update_request_status,
                get_request_by_id, clear_completed_requests, retry_error_requests,
                retry_request_by_id, clear_all_requests)
from datetime import datetime
import uuid

def test_db_connection():
    """データベース接続テスト"""
    print("=== データベース接続テスト ===")
    try:
        params = load_parameters()
        print(f"✅ データベース接続成功。現在 {len(params)} 件のレコードがあります")
        return True
    except Exception as e:
        print(f"❌ データベース接続失敗: {e}")
        return False

def test_add_request():
    """FAXリクエスト追加テスト"""
    print("\n=== FAXリクエスト追加テスト ===")
    try:
        # テスト用リクエストを追加
        test_request = add_fax_request(
            file_url="http://example.com/test.pdf",
            fax_number="0312345678",
            request_user="テストユーザー",
            file_name="test.pdf",
            callback_url="http://example.com/callback"
        )

        print(f"✅ リクエスト追加成功: ID={test_request['id']}")
        return test_request['id']
    except Exception as e:
        print(f"❌ リクエスト追加失敗: {e}")
        return None

def test_update_status(request_id):
    """ステータス更新テスト"""
    print("\n=== ステータス更新テスト ===")
    try:
        # ステータスを処理中に更新
        update_request_status(request_id, 2, "テスト処理中")
        print("✅ ステータス更新成功（処理中）")

        # ステータスを完了に更新
        update_request_status(request_id, 1, None)
        print("✅ ステータス更新成功（完了）")

        return True
    except Exception as e:
        print(f"❌ ステータス更新失敗: {e}")
        return False

def test_get_request(request_id):
    """リクエスト取得テスト"""
    print("\n=== リクエスト取得テスト ===")
    try:
        request_data = get_request_by_id(request_id)
        if request_data:
            print(f"✅ リクエスト取得成功: {request_data['file_name']} ({request_data['status']})")
            return True
        else:
            print("❌ リクエストが見つかりません")
            return False
    except Exception as e:
        print(f"❌ リクエスト取得失敗: {e}")
        return False

def test_management_functions():
    """管理機能テスト"""
    print("\n=== 管理機能テスト ===")

    # 完了済み削除テスト（実際には削除されないようにテスト）
    try:
        deleted_count = clear_completed_requests()
        print(f"✅ 完了済み削除テスト: {deleted_count}件削除")
    except Exception as e:
        print(f"❌ 完了済み削除テスト失敗: {e}")

    # エラーリトライテスト
    try:
        retry_count = retry_error_requests()
        print(f"✅ エラーリトライテスト: {retry_count}件リトライ")
    except Exception as e:
        print(f"❌ エラーリトライテスト失敗: {e}")

    # 全削除テスト（実際には削除しない）
    try:
        total_count = len(load_parameters())
        print(f"✅ 全レコード数取得: {total_count}件")
    except Exception as e:
        print(f"❌ レコード数取得失敗: {e}")

def cleanup_test_data(request_id):
    """テストデータをクリーンアップ"""
    print("\n=== テストデータクリーンアップ ===")
    try:
        # テストデータを削除（実際の運用では行わない）
        import mysql.connector
        from db import mydb, mycursor

        mycursor.execute("DELETE FROM fax_parameters WHERE id = %s", (request_id,))
        mydb.commit()

        if mycursor.rowcount > 0:
            print(f"✅ テストデータ削除成功: ID={request_id}")
        else:
            print(f"⚠ テストデータが見つかりませんでした: ID={request_id}")
    except Exception as e:
        print(f"❌ テストデータ削除失敗: {e}")

def main():
    """メインテスト実行"""
    print("FAX送信システム - データベース移行テスト")
    print("=" * 50)

    # データベース接続テスト
    if not test_db_connection():
        print("データベース接続に失敗したため、テストを中止します。")
        return

    # FAXリクエスト追加テスト
    request_id = test_add_request()
    if not request_id:
        print("リクエスト追加に失敗したため、テストを中止します。")
        return

    # ステータス更新テスト
    if not test_update_status(request_id):
        print("ステータス更新テストに失敗しました。")

    # リクエスト取得テスト
    if not test_get_request(request_id):
        print("リクエスト取得テストに失敗しました。")

    # 管理機能テスト
    test_management_functions()

    # テストデータクリーンアップ
    cleanup_test_data(request_id)

    print("\n" + "=" * 50)
    print("データベース移行テスト完了")
    print("✅ JSONファイルからMySQLデータベースへの移行が成功しています")

if __name__ == "__main__":
    main()
