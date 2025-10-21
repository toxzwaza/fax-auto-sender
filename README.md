# FAX送信API（非同期版）

Flaskを使用した非同期FAX送信APIです。ファイルURLとFAX番号を受け取り、バックグラウンドでFAX送信を実行します。

## 機能

- 非同期FAX送信処理
- ファイルURLからファイルをダウンロード（ローカルファイル対応）
- FAX番号への自動送信
- パラメータの履歴蓄積（parameter.json）
- ステータス管理（待機中/完了/エラー）
- リクエスト履歴の確認

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
    "fax_number": "0432119261"
}
```

**レスポンス:**
```json
{
    "success": true,
    "message": "FAX送信リクエストが登録されました",
    "request_id": "12345678-1234-1234-1234-123456789abc",
    "status": "pending"
}
```

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

## 設定

- FAXドライバー名: `FX 5570 FAX Driver`
- ポート: `5000`

## 注意事項

- Windows環境でのみ動作します
- FAXドライバーがインストールされている必要があります
- ファイルはPDF形式を想定しています
