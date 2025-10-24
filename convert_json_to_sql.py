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

    print('-- parameter.json から fax_parameters テーブルへのデータ移行SQL')
    print(f'-- 総レコード数: {len(data)}')
    print()

    print('INSERT INTO fax_parameters (id, file_url, fax_number, status, created_at, updated_at, error_message, converted_pdf_path, request_user, file_name, callback_url, order_destination) VALUES')

    values = []
    for record in data:
        id_val = record['id']
        file_url = record.get('file_url')
        fax_number = record.get('fax_number')
        status = record.get('status', 0)
        created_at = record.get('created_at')
        updated_at = record.get('updated_at')
        error_message = record.get('error_message')
        converted_pdf_path = record.get('converted_pdf_path')

        # JSONに含まれていないフィールドはNULL
        request_user = record.get('request_user')
        file_name = record.get('file_name')
        callback_url = record.get('callback_url')
        order_destination = record.get('order_destination')

        # SQLエスケープ
        file_url_sql = escape_sql_string(file_url)
        fax_number_sql = escape_sql_string(fax_number)
        error_message_sql = escape_sql_string(error_message)
        converted_pdf_path_sql = escape_sql_string(converted_pdf_path)
        request_user_sql = escape_sql_string(request_user)
        file_name_sql = escape_sql_string(file_name)
        callback_url_sql = escape_sql_string(callback_url)
        order_destination_sql = escape_sql_string(order_destination)

        value = f"('{id_val}', {file_url_sql}, {fax_number_sql}, {status}, '{created_at}', '{updated_at}', {error_message_sql}, {converted_pdf_path_sql}, {request_user_sql}, {file_name_sql}, {callback_url_sql}, {order_destination_sql})"
        values.append(value)

    # 各値をカンマで区切って出力
    for i, value in enumerate(values):
        comma = ',' if i < len(values) - 1 else ';'
        print(f'{value}{comma}')

    print()
    print('-- 完了後、以下のコマンドで確認できます:')
    print('-- SELECT COUNT(*) FROM fax_parameters;')
    print('-- SELECT * FROM fax_parameters LIMIT 5;')

if __name__ == '__main__':
    main()
