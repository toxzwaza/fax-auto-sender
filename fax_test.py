import win32api
import pyautogui
import pygetwindow as gw
import os
import time

# === 設定 ===
pdf_path = os.path.abspath("fax_test.pdf")
printer_name = "FX 5570 FAX Driver"
fax_number = "0432119261"

# === FAX送信ダイアログを開く ===
win32api.ShellExecute(0, "printto", pdf_path, f'"{printer_name}"', ".", 1)
print("FAXダイアログを起動中...")

# === ダイアログが開くまで待機 ===
fax_window = None
for i in range(20):  # 最大20秒待機
    time.sleep(1)
    titles = [t for t in gw.getAllTitles() if "ファクス送信" in t]
    if titles:
        fax_window = gw.getWindowsWithTitle(titles[0])[0]
        print(f"FAXダイアログ検出: {titles[0]}")
        break
else:
    raise RuntimeError("FAXダイアログが見つかりませんでした。")

# === FAXダイアログをアクティブ化 ===
fax_window.activate()
time.sleep(0.8)

# === 宛先番号入力（フォーカスは既に宛先欄） ===
pyautogui.typewrite(fax_number)
print(f"宛先番号 {fax_number} を入力しました。")

time.sleep(0.5)

# === TABキーを9回押して「送信開始」ボタンにフォーカス ===
pyautogui.press("tab", presses=9, interval=0.15)
print("Tabキーを9回送信しました。")

time.sleep(0.3)

# === Enterで送信開始 ===
pyautogui.press("enter")
print("『送信開始』を押下しました。")

# === 警告ウィンドウ処理 ===
for i in range(10):
    time.sleep(0.5)
    warnings = [t for t in gw.getAllTitles() if "警告" in t]
    if warnings:
        w = gw.getWindowsWithTitle(warnings[0])[0]
        w.activate()
        time.sleep(0.2)
        pyautogui.press("enter")
        print("警告ダイアログの『OK』を押しました。")
        break
else:
    print("⚠ 警告ダイアログは検出されませんでした。")
