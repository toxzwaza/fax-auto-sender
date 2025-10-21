import win32print
import win32api
import os

pdf_path = os.path.abspath("fax_test.pdf")
printer_name = "FX 5570 FAX Driver"

# プリンタハンドルを取得
printer = win32print.OpenPrinter(printer_name)
try:
    # 印刷ジョブを開始
    hJob = win32print.StartDocPrinter(printer, 1, ("FAX送信テスト", None, "RAW"))
    win32print.StartPagePrinter(printer)

    # ファイルを送信
    with open(pdf_path, "rb") as f:
        win32print.WritePrinter(printer, f.read())

    win32print.EndPagePrinter(printer)
    win32print.EndDocPrinter(printer)
    print("FAXドライバーに印刷ジョブを送信しました。")

finally:
    win32print.ClosePrinter(printer)
