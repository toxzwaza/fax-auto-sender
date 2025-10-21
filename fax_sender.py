#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAX送信処理モジュール
"""

import os
import time
import win32api
import pyautogui
import pygetwindow as gw
from datetime import datetime

# FAX送信設定
PRINTER_NAME = "FX 5570 FAX Driver"

def send_fax(pdf_path, fax_number):
    """FAX送信を実行"""
    try:
        print(f"FAX送信開始: {pdf_path} -> {fax_number}")
        
        # FAX送信ダイアログを開く
        win32api.ShellExecute(0, "printto", pdf_path, f'"{PRINTER_NAME}"', ".", 1)
        print("FAXダイアログを起動中...")

        # ダイアログが開くまで待機
        fax_window = None
        for i in range(30):  # 最大30秒待機
            time.sleep(1)
            titles = [t for t in gw.getAllTitles() if "ファクス送信" in t]
            if titles:
                fax_window = gw.getWindowsWithTitle(titles[0])[0]
                print(f"FAXダイアログ検出: {titles[0]}")
                break
            print(f"FAXダイアログ待機中... ({i+1}/30)")
        else:
            raise RuntimeError("FAXダイアログが見つかりませんでした。")

        # ウィンドウを確実にアクティブ化
        print("FAXダイアログをアクティブ化中...")
        fax_window.activate()
        time.sleep(1.0)
        
        # ウィンドウが最前面に来るまで確認
        for attempt in range(5):
            if fax_window.isActive:
                print("FAXダイアログがアクティブになりました")
                break
            else:
                print(f"アクティブ化再試行 {attempt + 1}/5")
                fax_window.activate()
                time.sleep(0.5)
        else:
            print("⚠ ウィンドウのアクティブ化に失敗しましたが、続行します")

        # 宛先番号入力（より確実に）
        print(f"宛先番号 {fax_number} を入力中...")
        pyautogui.click(fax_window.left + 100, fax_window.top + 100)  # ダイアログ内をクリック
        time.sleep(0.3)
        pyautogui.typewrite(fax_number, interval=0.1)  # より遅い入力
        print(f"宛先番号 {fax_number} を入力しました。")

        time.sleep(0.8)

        # TABキーを9回押して「送信開始」ボタンにフォーカス
        print("送信開始ボタンにフォーカス移動中...")
        pyautogui.press("tab", presses=9, interval=0.2)  # より遅い間隔
        print("Tabキーを9回送信しました。")

        time.sleep(0.5)

        # Enterで送信開始
        print("送信開始ボタンを押下中...")
        pyautogui.press("enter")
        print("『送信開始』を押下しました。")

        # 警告ウィンドウ処理（より確実に）
        print("警告ダイアログをチェック中...")
        for i in range(15):  # より長い待機時間
            time.sleep(0.5)
            warnings = [t for t in gw.getAllTitles() if "警告" in t]
            if warnings:
                w = gw.getWindowsWithTitle(warnings[0])[0]
                print(f"警告ダイアログ検出: {warnings[0]}")
                w.activate()
                time.sleep(0.5)
                pyautogui.press("enter")
                print("警告ダイアログの『OK』を押しました。")
                break
            print(f"警告ダイアログ待機中... ({i+1}/15)")
        else:
            print("⚠ 警告ダイアログは検出されませんでした。")

        print("FAX送信処理が完了しました")
        return True

    except Exception as e:
        print(f"FAX送信エラー: {e}")
        return False

def send_fax_with_retry(pdf_path, fax_number, max_retries=3):
    """FAX送信をリトライ機能付きで実行"""
    for attempt in range(max_retries):
        print(f"FAX送信試行 {attempt + 1}/{max_retries}")
        
        if send_fax(pdf_path, fax_number):
            print(f"FAX送信成功: {fax_number}")
            return True
        else:
            print(f"FAX送信失敗: {fax_number} (試行 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                print(f"5秒後に再試行します...")
                time.sleep(5)
    
    print(f"FAX送信最終失敗: {fax_number} (全{max_retries}回試行)")
    return False

def cleanup_temp_files():
    """一時ファイルをクリーンアップ"""
    try:
        import glob
        temp_files = glob.glob("temp_fax_*.pdf")
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
                print(f"一時ファイルを削除: {temp_file}")
            except:
                pass
    except Exception as e:
        print(f"一時ファイルクリーンアップエラー: {e}")

if __name__ == "__main__":
    # テスト用
    test_pdf = "fax_test.pdf"
    test_fax_number = "0432119261"
    
    if os.path.exists(test_pdf):
        print("FAX送信テストを開始...")
        success = send_fax_with_retry(test_pdf, test_fax_number)
        if success:
            print("✅ FAX送信テスト成功")
        else:
            print("❌ FAX送信テスト失敗")
    else:
        print(f"テストファイルが見つかりません: {test_pdf}")
