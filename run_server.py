#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAX自動送信Webアプリケーション起動スクリプト
"""

import sys
import os
import webbrowser
import time
import threading
from web_app import app, socketio, fax_worker

def open_browser():
    """ブラウザを自動で開く"""
    time.sleep(2)  # サーバー起動を待つ
    webbrowser.open('http://localhost:5000')

def main():
    """メイン関数"""
    print("=" * 60)
    print("📠 FAX自動送信Webアプリケーション")
    print("=" * 60)
    print()
    
    # 必要なファイルの存在確認
    required_files = [
        'fax_service.py',
        'web_app.py',
        'logger.py',
        'templates/index.html'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ 以下のファイルが見つかりません:")
        for file in missing_files:
            print(f"   - {file}")
        print()
        print("必要なファイルが揃っているか確認してください。")
        sys.exit(1)
    
    print("✅ 必要なファイルが確認できました")
    print()
    
    # FAXドライバーの確認
    try:
        import win32print
        printers = [printer[2] for printer in win32print.EnumPrinters(2)]
        fax_printers = [p for p in printers if 'FAX' in p.upper()]
        
        if fax_printers:
            print("✅ FAXドライバーが見つかりました:")
            for printer in fax_printers:
                print(f"   - {printer}")
        else:
            print("⚠️  FAXドライバーが見つかりません")
            print("   FX 5570 FAX Driver がインストールされているか確認してください")
        print()
        
    except ImportError:
        print("❌ pywin32がインストールされていません")
        print("   pip install pywin32 を実行してください")
        sys.exit(1)
    
    # ブラウザを自動で開くスレッドを開始
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    print("🚀 Webサーバーを起動中...")
    print("📱 ブラウザで http://localhost:5000 にアクセスしてください")
    print()
    print("💡 使用方法:")
    print("   1. FAX番号を入力")
    print("   2. PDFファイルのURLを入力")
    print("   3. FAX送信ボタンをクリック")
    print("   4. キューシステムで順次処理されます")
    print("   5. 管理画面で送信状況を確認")
    print()
    print("🔄 キューシステム:")
    print("   - 複数クライアントからの同時送信に対応")
    print("   - 優先度に基づく処理順序")
    print("   - 5秒間隔での自動処理")
    print()
    print("🛑 終了するには Ctrl+C を押してください")
    print("=" * 60)
    
    # FAX送信ワーカーを開始
    print("\n🔄 FAX送信ワーカーを起動中...")
    fax_worker.start()
    print("✅ FAX送信ワーカーが起動しました")
    print()
    
    try:
        # Webサーバーを起動
        socketio.run(app, debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 FAX送信ワーカーを停止中...")
        fax_worker.stop()
        print("👋 FAX自動送信アプリケーションを終了します")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ サーバー起動エラー: {e}")
        fax_worker.stop()
        sys.exit(1)

if __name__ == '__main__':
    main()
