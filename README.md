# 📠 FAX自動送信Webアプリケーション

Windows環境でFAX送信を自動化し、WebアプリケーションとWebSocketを使用してリアルタイムで送信状況を監視できるシステムです。

## 🚀 機能

- **Web UI**: ブラウザからFAX送信を実行
- **管理画面**: FAX送信履歴とステータス管理
- **Laravel連携**: Laravel/Inertia/Vue.jsアプリからのAPI連携
- **キューシステム**: 複数クライアントからの同時送信に対応
- **優先度処理**: 優先度に基づく処理順序制御
- **リアルタイム監視**: WebSocketで送信状況をリアルタイム表示
- **PDF URL対応**: インターネット上のPDFファイルを直接送信
- **データベース管理**: SQLiteによる送信履歴の永続化
- **ログ機能**: 送信履歴とエラーログを記録
- **API認証**: セキュアなAPI認証機能

## 📋 必要な環境

- Windows OS
- Python 3.8以上
- FX 5570 FAX Driver（または互換FAXドライバー）

## 🛠️ インストール

1. **依存関係のインストール**
   ```bash
   pip install -r requirements.txt
   ```

2. **FAXドライバーの確認**
   - FX 5570 FAX Driverがインストールされていることを確認
   - Windowsのプリンタ一覧にFAXドライバーが表示されることを確認

## 🎯 使用方法

### 1. サーバーの起動
```bash
python run_server.py
```

### 2. Webアプリケーションにアクセス
- **送信画面**: `http://localhost:5000` - FAX送信用のWeb UI
- **管理画面**: `http://localhost:5000/admin` - 送信履歴とステータス管理
- 自動でブラウザが開きます

### 3. FAX送信（Web UI）
1. **送信先FAX番号**を入力（例: 03-1234-5678）
2. **PDFファイルURL**を入力（例: https://example.com/document.pdf）
3. **FAX送信**ボタンをクリック
4. リアルタイムで送信状況を確認

### 4. Laravelアプリからの送信
詳細は `LARAVEL_INTEGRATION.md` を参照してください。

## 🔄 キューシステム

### 処理フロー
1. **API受信**: クライアントからFAX送信リクエストを受信
2. **キュー追加**: データベースにジョブを追加（`queued`ステータス）
3. **定期処理**: 5秒間隔でワーカースレッドがキューをチェック
4. **順次処理**: 優先度と作成日時に基づいて順次処理
5. **ステータス更新**: 処理状況をリアルタイムで更新

### 優先度システム
- **High (3)**: 緊急度の高い送信
- **Normal (2)**: 通常の送信（デフォルト）
- **Low (1)**: 低優先度の送信

### ステータス遷移
```
queued → processing → starting → downloading → printing → sending → completed
   ↓
  error (エラー時)
```

## 📁 ファイル構成

```
fax-auto-sender/
├── main.py                    # 元のFAX送信スクリプト
├── fax_service.py             # FAX送信サービス（改修版）
├── fax_worker.py              # FAX送信ワーカー（キュー処理）
├── web_app.py                 # Flask Webアプリケーション
├── database.py                # データベース管理
├── logger.py                  # ログ機能
├── run_server.py              # サーバー起動スクリプト
├── requirements.txt           # 依存関係
├── templates/
│   ├── index.html             # Web UI（送信画面）
│   └── admin.html             # 管理画面
├── logs/                      # ログファイル（自動生成）
├── fax_history.db            # SQLiteデータベース（自動生成）
├── LARAVEL_INTEGRATION.md     # Laravel連携ドキュメント
└── fax_test.pdf              # テスト用PDF
```

## 🔧 API仕様

### FAX送信API
```http
POST /api/send_fax
Content-Type: application/json

{
    "fax_number": "03-1234-5678",
    "pdf_url": "https://example.com/document.pdf"
}
```

### レスポンス
```json
{
    "success": true,
    "job_id": "uuid-string",
    "message": "FAX送信を開始しました"
}
```

### ジョブステータスAPI
```http
GET /api/job_status/{job_id}
```

## 📊 WebSocketイベント

### 接続
```javascript
socket.on('connect', function() {
    console.log('サーバーに接続しました');
});
```

### ジョブ更新
```javascript
socket.on('job_update', function(data) {
    console.log('ステータス:', data.status);
    console.log('メッセージ:', data.message);
});
```

## 📝 ログ

- ログファイルは `logs/` ディレクトリに保存
- ファイル名: `fax_YYYYMMDD.log`
- 送信開始、ステータス更新、完了、エラーを記録

## ⚠️ 注意事項

1. **FAXドライバー**: FX 5570 FAX Driverが正しくインストールされている必要があります
2. **PDF URL**: アクセス可能なPDFファイルのURLを指定してください
3. **ネットワーク**: PDFファイルのダウンロードにインターネット接続が必要です
4. **権限**: Windowsのプリンタアクセス権限が必要です

## 🐛 トラブルシューティング

### FAXドライバーが見つからない
- Windowsのプリンタ設定でFAXドライバーがインストールされているか確認
- ドライバー名が "FX 5570 FAX Driver" と一致しているか確認

### PDFダウンロードエラー
- PDF URLが正しくアクセス可能か確認
- ネットワーク接続を確認

### WebSocket接続エラー
- ファイアウォール設定を確認
- ポート5000が使用可能か確認

## 📞 サポート

問題が発生した場合は、ログファイル（`logs/fax_YYYYMMDD.log`）を確認してください。
