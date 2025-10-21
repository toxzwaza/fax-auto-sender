from pywinauto.application import Application
import win32api
import pygetwindow as gw
import pyautogui
import os
import time

# === 設定 ===
pdf_path = os.path.abspath("fax_test.pdf")
printer_name = "FX 5570 FAX Driver"
fax_number = "0432119261"

# === FAX送信ダイアログを開く ===
win32api.ShellExecute(0, "printto", pdf_path, f'"{printer_name}"', ".", 1)
print("FAXダイアログを起動中...")
time.sleep(3.5)

try:
    # === 「ファクス送信」ウィンドウに接続 ===
    app = Application(backend="uia").connect(title_re=".*ファクス送信の設定.*", timeout=10)
    dlg = app.window(title_re=".*ファクス送信の設定.*")

    # === 宛先番号入力 ===
    edit_box = dlg.child_window(title_re=".*宛先番号.*", control_type="Edit")
    edit_box.set_focus()
    edit_box.type_keys(fax_number, with_spaces=True)
    print(f"宛先番号 {fax_number} を入力しました。")

    time.sleep(0.8)

    # === 「送信開始」クリック ===
    dlg.child_window(title="送信開始", control_type="Button").click_input()
    print("『送信開始』ボタンをクリックしました。")

    # === 「警告」ダイアログを pygetwindow で探索 ===
    print("警告ウィンドウを探索中...")
    for i in range(10):  # 最大5秒間スキャン
        warning_windows = [w for w in gw.getAllTitles() if "警告" in w]
        if warning_windows:
            print(f"警告ウィンドウ検出: {warning_windows[0]}")
            # フォーカスをそのウィンドウに移す
            win = gw.getWindowsWithTitle(warning_windows[0])[0]
            win.activate()
            time.sleep(0.5)
            # 「OK」ボタンの位置をクリック（画面中央や右下に出ることが多い）
            pyautogui.press("enter")  # OKを押すショートカット
            print("『OK』を自動クリックしました。")
            break
        time.sleep(0.5)
    else:
        print("⚠ 警告ダイアログが見つかりませんでした。")

except Exception as e:
    print("FAXダイアログ操作中にエラーが発生しました:", e)
