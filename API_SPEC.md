# FAX送信API仕様書

## エンドポイント一覧

### 1. `/send_fax` - FAX送信リクエスト（URL指定）

**メソッド:** `POST`

**リクエストボディ (JSON):**

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `file_url` | string | ✅ | 送信するファイルのURL（`file://` または `http(s)://`） |
| `fax_number` | string | ✅ | FAX送信先の番号 |
| `request_user` | string | ❌ | 依頼者名 |
| `file_name` | string | ❌ | ファイル名 |
| `order_destination` | string | ❌ | 発注先 |
| `callback_url` | string | ❌ | 通知先URL（FAX送信完了時にGETリクエストを送信） |

**リクエスト例:**

```json
{
  "file_url": "file:///path/to/document.pdf",
  "fax_number": "0312345678",
  "request_user": "山田太郎",
  "file_name": "見積書_2025年10月.pdf",
  "order_destination": "ABC株式会社",
  "callback_url": "https://example.com/callback"
}
```

**レスポンス例（成功）:**

```json
{
  "success": true,
  "message": "FAX送信リクエストを登録しました",
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "request_user": "山田太郎",
  "file_name": "見積書_2025年10月.pdf",
  "order_destination": "ABC株式会社",
  "callback_url": "https://example.com/callback",
  "fax_number": "0312345678",
  "created_at": "2025-10-22T15:30:45.123456"
}
```

**レスポンス例（エラー）:**

```json
{
  "success": false,
  "error": "file_urlとfax_numberは必須です"
}
```

---

### 2. `/upload_and_send_fax` - ファイルアップロード＆FAX送信

**メソッド:** `POST`

**リクエスト (multipart/form-data):**

| パラメータ | 型 | 必須 | 説明 |
|---|---|---|---|
| `file` | file | ✅ | 送信するファイル（PDF, PNG, JPG, TIFF） |
| `fax_number` | string | ✅ | FAX送信先の番号 |
| `request_user` | string | ❌ | 依頼者名 |
| `file_name` | string | ❌ | ファイル名（未指定の場合はアップロードファイル名を使用） |
| `order_destination` | string | ❌ | 発注先 |
| `callback_url` | string | ❌ | 通知先URL |

**レスポンス例（成功）:**

```json
{
  "success": true,
  "message": "ファイルをアップロードし、FAX送信リクエストを登録しました",
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "request_user": "山田太郎",
  "file_name": "document.pdf",
  "order_destination": "ABC株式会社",
  "callback_url": "https://example.com/callback",
  "fax_number": "0312345678",
  "uploaded_file": "uploads/document_20251022_153045.pdf",
  "created_at": "2025-10-22T15:30:45.123456"
}
```

---

### 3. `/status/<request_id>` - ステータス確認

**メソッド:** `GET`

**レスポンス例:**

```json
{
  "success": true,
  "request": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "file_url": "file:///path/to/document.pdf",
    "fax_number": "0312345678",
    "status": 1,
    "request_user": "山田太郎",
    "file_name": "見積書.pdf",
    "callback_url": "https://example.com/callback",
    "created_at": "2025-10-22T15:30:45.123456",
    "updated_at": "2025-10-22T15:31:10.654321",
    "error_message": null,
    "converted_pdf_path": "/path/to/converted.pdf"
  }
}
```

---

### 4. `/requests` - 全リクエスト一覧

**メソッド:** `GET`

**レスポンス例:**

```json
{
  "success": true,
  "requests": [
    {
      "id": "...",
      "file_url": "...",
      "fax_number": "...",
      "status": 1,
      "request_user": "山田太郎",
      "file_name": "見積書.pdf",
      "callback_url": "https://example.com/callback",
      ...
    }
  ],
  "total": 10
}
```

---

## リクエスト詳細画面

個別のFAX送信リクエストの詳細をHTMLで表示します。

**URL:** `/<request_id>`

**メソッド:** `GET`

**例:** `http://localhost:5000/a1b2c3d4-e5f6-7890-abcd-ef1234567890`

**レスポンス:** HTML（詳細画面）

**表示内容:**
- リクエストID
- ステータス（待機中/処理中/完了/エラー）
- 依頼者名
- ファイル名
- 発注先
- FAX番号
- コールバックURL設定状況（⭕/❌）
- 作成日時・更新日時
- エラーメッセージ（エラー時）
- 元ファイルと変換PDFへのリンク
- 操作ボタン（再送、ステータス更新など）

**特徴:**
- 管理画面のIDカラムからリンク
- 自動更新機能（処理中・待機中の場合、30秒ごと）
- レスポンシブデザイン
- ファイルプレビューへの直接リンク

---

## コールバック通知

`callback_url` が設定されている場合、**FAX送信が成功した時点**で、指定されたURLに対してGETリクエストが自動的に送信されます。

### コールバック通知のタイミング

- **成功時のみ**: FAX送信が正常に完了したとき
- **失敗時**: 通知なし

### コールバックリクエスト形式

**メソッド:** `GET`

**パラメータ:** なし（URLをそのまま呼び出し）

### コールバック例

設定したURLがそのまま呼び出されます：
```
http://example.com/callback
```

クエリパラメータや追加情報は付加されません。シンプルに成功通知のみが送信されます。

### コールバック受信サーバーの実装例

**Python (Flask):**
```python
from flask import Flask

app = Flask(__name__)

@app.route('/callback', methods=['GET'])
def receive_callback():
    # FAX送信が成功したことを検知
    print("✅ FAX送信完了通知を受信しました")
    
    # ここで必要な処理を実行（データベース更新、メール送信など）
    
    return {"status": "ok"}, 200

if __name__ == '__main__':
    app.run(port=8888)
```

**Node.js (Express):**
```javascript
const express = require('express');
const app = express();

app.get('/callback', (req, res) => {
    console.log('✅ FAX送信完了通知を受信しました');
    res.json({ status: 'ok' });
});

app.listen(8888);
```

### 注意事項

1. **タイムアウト**: コールバックリクエストは10秒でタイムアウトします
2. **エラーハンドリング**: コールバック送信が失敗しても、FAX送信処理自体には影響しません
3. **リトライなし**: コールバック送信は1回のみで、失敗時の自動リトライはありません
4. **成功時のみ**: FAX送信が失敗した場合はコールバックは送信されません
5. **パラメータなし**: 詳細情報が必要な場合は、別途ステータス確認API (`/status/{request_id}`) を呼び出してください

---

## ステータスコード

| ステータス | 値 | 説明 |
|---|---|---|
| 待機中 | `0` | 処理待ち |
| 完了 | `1` | FAX送信完了 |
| エラー | `-1` | FAX送信失敗 |
| 処理中 | `2` | 現在処理中 |

---

## レスポンスフィールドの説明

### IDフィールド
- **`id`**: 生成されたリクエストID（UUID形式）
- **`request_id`**: `id` と同じ値（後方互換性のため両方返却）

### オプションフィールド
- **`request_user`**: 依頼者名（未指定の場合は `null`）
- **`file_name`**: ファイル名（未指定の場合は `null`）
- **`callback_url`**: コールバックURL（未指定の場合は `null`）

---

## 使用例

### Python

```python
import requests

# 基本的な使い方
response = requests.post('http://localhost:5000/send_fax', json={
    "file_url": "file:///path/to/file.pdf",
    "fax_number": "0312345678"
})
result = response.json()
print(f"生成されたID: {result['id']}")

# すべてのパラメータを指定（コールバック付き）
response = requests.post('http://localhost:5000/send_fax', json={
    "file_url": "file:///path/to/file.pdf",
    "fax_number": "0312345678",
    "request_user": "山田太郎",
    "file_name": "見積書.pdf",
    "callback_url": "https://example.com/callback"  # FAX送信完了時に通知
})
result = response.json()
print(f"生成されたID: {result['id']}")
print(f"依頼者: {result['request_user']}")
print(f"コールバックURL: {result['callback_url']}")
```

### cURL

```bash
# 基本的な使い方
curl -X POST http://localhost:5000/send_fax \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "file:///path/to/file.pdf",
    "fax_number": "0312345678"
  }'

# すべてのパラメータを指定
curl -X POST http://localhost:5000/send_fax \
  -H "Content-Type: application/json" \
  -d '{
    "file_url": "file:///path/to/file.pdf",
    "fax_number": "0312345678",
    "request_user": "山田太郎",
    "file_name": "見積書.pdf",
    "callback_url": "https://example.com/callback"
  }'

# ファイルアップロード
curl -X POST http://localhost:5000/upload_and_send_fax \
  -F "file=@document.pdf" \
  -F "fax_number=0312345678" \
  -F "request_user=山田太郎" \
  -F "file_name=見積書.pdf" \
  -F "callback_url=https://example.com/callback"
```

---

## 管理画面

管理画面にアクセス: `http://localhost:5000`

管理画面では以下の情報が表示されます：
- ID
- 依頼者（`request_user`）
- ファイル名（`file_name`）
- ファイル（元ファイルのリンク）
- 変換PDF（変換後PDFのリンク）
- FAX番号
- コールバック（⭕/❌で設定有無を表示）
- ステータス
- 作成日時
- 更新日時
- エラーメッセージ
- 操作（再送ボタン）

---

## 注意事項

1. **後方互換性**: `request_id` と `id` の両方が返されますが、新規開発では `id` の使用を推奨します。
2. **オプションパラメータ**: `request_user`, `file_name`, `callback_url` は任意です。指定しない場合は `null` が保存されます。
3. **ファイルアップロード**: `file_name` を指定しない場合、アップロードされたファイル名が自動的に使用されます。

