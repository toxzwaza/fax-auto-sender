#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parameter.json を MySQL INSERT文に変換するスクリプト
"""

import json
import os

def escape_sql_string(value):
    """SQL文字列をエスケープ"""
    if value is None:
        return 'NULL'
    # バックスラッシュをエスケープ
    escaped = str(value).replace('\\', '\\\\')
    # シングルクォートをエスケープ
    escaped = escaped.replace("'", "\\'")
    return f"'{escaped}'"

def main():
    # parameter.jsonを読み込み
    with open('parameter.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    print('parameter.json から fax_parameters テーブルへのデータ移行開始')
    print(f'総レコード数: {len(data)}')
    print()

    # db.pyから関数をインポート
    try:
        from db import add_fax_request, load_parameters
        print("db.pyのインポート成功")
    except ImportError as e:
        print(f"db.pyのインポート失敗: {e}")
        print("MySQL Connectorがインストールされているか確認してください")
        return

    # 既存データの確認
    try:
        existing_count = len(load_parameters())
        print(f'移行前の既存レコード数: {existing_count}')
    except Exception as e:
        print(f"既存データ確認エラー: {e}")
        return

    success_count = 0
    error_count = 0

    for i, record in enumerate(data, 1):
        print(f"\n[{i}/{len(data)}] レコード処理開始")
        print(f"   ID: {record.get('id', '不明')}")
        print(f"   FAX番号: {record.get('fax_number', '不明')}")
        print(f"   ステータス: {record.get('status', '不明')}")

        try:
            # add_fax_request関数を使用してレコードを追加
            result = add_fax_request(
                file_url=record.get('file_url'),
                fax_number=record.get('fax_number'),
                request_user=record.get('request_user'),
                file_name=record.get('file_name'),
                callback_url=record.get('callback_url'),
                order_destination=record.get('order_destination')
            )

            if result:
                success_count += 1
                print(f"[{i}] レコード追加成功: {result['id']}")
            else:
                error_count += 1
                print(f"[{i}] レコード追加失敗: 結果がNone")

        except Exception as e:
            error_count += 1
            print(f"[{i}] レコード追加エラー: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("移行結果サマリー")
    print(f"処理対象: {len(data)} 件")
    print(f"成功: {success_count} 件")
    print(f"エラー: {error_count} 件")

    # 最終確認
    try:
        final_count = len(load_parameters())
        print(f"移行後の総レコード数: {final_count}")
        print(f"追加されたレコード数: {final_count - existing_count}")
    except Exception as e:
        print(f"最終確認エラー: {e}")

    if error_count == 0:
        print("\n移行が完全に成功しました！")
    else:
        print(f"\n{error_count}件のエラーが発生しました。詳細を確認してください。")

if __name__ == '__main__':
    main()
