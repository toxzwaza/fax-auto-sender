# FAX送信API（非同期版）

Flaskを使用した非同期FAX送信APIです。ファイルURLとFAX番号を受け取り、バックグラウンドでFAX送信を実行します。

## 機能

- 非同期FAX送信処理
- ファイルURLからファイルをダウンロード（ローカルファイル対応）
- FAX番号への自動送信
- パラメータの履歴蓄積（parameter.json）
- ステータス管理（待機中/完了/エラー）
- リクエスト履歴の確認
- **🆕 コールバック通知機能**（FAX送信完了時に指定URLへ通知）
- **🆕 依頼者名・ファイル名の管理**
- **🆕 画像ファイルの自動PDF変換**（PNG, JPG, TIFF対応）
- **🆕 Web管理画面**（リクエスト一覧、再送、削除機能）

## インストール

```bash
pip install -r requirements.txt
```

## 使用方法

### サーバー起動

```bash
python app.py
```

サーバーは `http://localhost:5000` で起動します。

### APIエンドポイント

#### FAX送信（非同期）

**POST** `/send_fax`

**リクエストボディ:**
```json
{
    "file_url": "https://example.com/document.pdf",
    "fax_number": "0432119261",
    "request_user": "山田太郎",          // オプション：依頼者名
    "file_name": "見積書.pdf",           // オプション：ファイル名
    "callback_url": "https://example.com/callback"  // オプション：完了通知先URL
}
```

**レスポンス:**
```json
{
    "success": true,
    "message": "FAX送信リクエストが登録されました",
    "id": "12345678-1234-1234-1234-123456789abc",
    "request_id": "12345678-1234-1234-1234-123456789abc",
    "status": "pending",
    "request_user": "山田太郎",
    "file_name": "見積書.pdf",
    "callback_url": "https://example.com/callback",
    "fax_number": "0432119261",
    "created_at": "2025-10-22T15:30:45.123456"
}
```

**コールバック通知（callback_url設定時）:**

FAX送信が**成功**すると、指定されたURLにGETリクエストが送信されます（パラメータなし）：
```
https://example.com/callback
```

※失敗時は通知されません。シンプルな成功通知のみです。

#### リクエストステータス確認

**GET** `/status/{request_id}`

**レスポンス:**
```json
{
    "success": true,
    "request": {
        "id": "12345678-1234-1234-1234-123456789abc",
        "file_url": "https://example.com/document.pdf",
        "fax_number": "0432119261",
        "status": 1,
        "created_at": "2024-01-01T12:00:00.000000",
        "updated_at": "2024-01-01T12:01:00.000000",
        "error_message": null
    }
}
```

#### すべてのリクエスト取得

**GET** `/requests`

**レスポンス:**
```json
{
    "success": true,
    "requests": [...],
    "total": 5
}
```

#### ヘルスチェック

**GET** `/health`

**レスポンス:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00.000000"
}
```

### ステータスコード

- `0`: 待機中
- `1`: 完了
- `2`: 処理中
- `-1`: エラー

### 管理画面

ブラウザで `http://localhost:5000` にアクセスすると、Web管理画面が表示されます。

**機能:**
- リクエスト一覧表示（依頼者、ファイル名、発注先、コールバック設定状況など）
- **🆕 絞り込み検索機能**（依頼者、ファイル名、発注先、FAX番号、ステータスで検索）
- IDをクリックすると詳細画面に遷移
- 送信ファイル・変換PDFのプレビュー
- エラー送信の再送
- 完了済み送信の一括削除
- 統計情報の表示

### 詳細画面

`http://localhost:5000/<request_id>` でアクセスすると、個別リクエストの詳細画面が表示されます。

**表示内容:**
- ステータス（待機中/処理中/完了/エラー）
- 基本情報（依頼者、ファイル名、FAX番号、コールバックURL設定状況）
- 作成日時・更新日時
- エラーメッセージ（エラー時）
- 元ファイルと変換PDFへのリンク
- 再送ボタン（エラー時）
- 自動更新機能（処理中・待機中の場合、30秒ごとに更新）

### テストツール

#### 基本テスト
```bash
python test_new_parameters.py
```

新しいパラメータ（request_user, file_name, callback_url）の動作を確認できます。

#### コールバック機能テスト
```bash
python test_callback.py
```

コールバック受信サーバーを起動して、コールバック通知の動作を確認できます。

#### 詳細画面テスト
```bash
python test_detail_page.py
```

詳細画面の表示機能をテストし、アクセスURLを表示します。

### 詳細なAPI仕様

詳細なAPI仕様書は [API_SPEC.md](./API_SPEC.md) を参照してください。

- 全エンドポイントの詳細
- コールバック通知の仕様
- リクエスト/レスポンスの例
- 使用例（Python、cURL）

## 設定

- FAXドライバー名: `FX 5570 FAX Driver`
- ポート: `5000`

## 注意事項

- Windows環境でのみ動作します
- FAXドライバーがインストールされている必要があります
- ファイルはPDF形式を想定しています
