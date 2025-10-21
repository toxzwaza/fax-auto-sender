import win32api
import os
import requests
import tempfile
import threading
from datetime import datetime
import json
import time
import pygetwindow as gw
import pyautogui
from pywinauto.application import Application
from logger import fax_logger

class FaxService:
    def __init__(self, printer_name="FX 5570 FAX Driver"):
        self.printer_name = printer_name
        self.status_callbacks = []
    
    def add_status_callback(self, callback):
        """ステータス更新のコールバック関数を追加"""
        self.status_callbacks.append(callback)
    
    def emit_status(self, status, message, data=None):
        """ステータス更新を通知"""
        status_data = {
            'status': status,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        for callback in self.status_callbacks:
            try:
                callback(status_data)
            except Exception as e:
                print(f"コールバック実行エラー: {e}")
    
    def download_file(self, file_url):
        """ファイルをURLからダウンロード（PDF/画像対応）"""
        try:
            # ローカルファイルの場合
            if file_url.startswith('file:///'):
                local_path = file_url.replace('file:///', '').replace('/', os.sep)
                if os.path.exists(local_path):
                    self.emit_status('downloading', 'ローカルファイルを読み込み中...')
                    return local_path
                else:
                    raise Exception(f'ローカルファイルが見つかりません: {local_path}')
            
            self.emit_status('downloading', 'ファイルをダウンロード中...')
            
            response = requests.get(file_url, timeout=30)
            response.raise_for_status()
            
            # ファイル拡張子を取得
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type.lower():
                ext = '.pdf'
            elif 'image' in content_type.lower():
                if 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                    ext = '.jpg'
                elif 'png' in content_type.lower():
                    ext = '.png'
                elif 'gif' in content_type.lower():
                    ext = '.gif'
                else:
                    ext = '.jpg'  # デフォルト
            else:
                # URLから拡張子を推測
                if file_url.lower().endswith('.pdf'):
                    ext = '.pdf'
                elif file_url.lower().endswith(('.jpg', '.jpeg')):
                    ext = '.jpg'
                elif file_url.lower().endswith('.png'):
                    ext = '.png'
                elif file_url.lower().endswith('.gif'):
                    ext = '.gif'
                else:
                    ext = '.pdf'  # デフォルト
            
            # 一時ファイルに保存
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_file.write(response.content)
            temp_file.close()
            
            self.emit_status('downloaded', 'ファイルのダウンロード完了')
            return temp_file.name
            
        except Exception as e:
            self.emit_status('error', f'ファイルダウンロードエラー: {str(e)}')
            raise
    
    def send_fax(self, fax_number, file_url, job_id=None):
        """FAX送信を実行（pywinauto使用）"""
        if job_id is None:
            job_id = f"fax_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        file_path = None
        is_temp_file = False
        
        try:
            # ログに記録
            fax_logger.log_fax_start(job_id, fax_number, file_url)
            
            self.emit_status('starting', f'FAX送信を開始します (ジョブID: {job_id})', {
                'job_id': job_id,
                'fax_number': fax_number,
                'file_url': file_url
            })
            
            # ファイルをダウンロード
            file_path = self.download_file(file_url)
            
            # ローカルファイル以外は一時ファイルとして削除対象
            if not file_url.startswith('file:///'):
                is_temp_file = True
            
            # FAXダイアログを開く
            self.emit_status('connecting', 'FAXダイアログを起動中...')
            win32api.ShellExecute(0, "printto", file_path, f'"{self.printer_name}"', ".", 1)
            time.sleep(3.5)
            
            try:
                # 「ファクス送信」ウィンドウに接続
                self.emit_status('printing', 'FAX送信ダイアログに接続中...')
                app = Application(backend="uia").connect(title_re=".*ファクス送信の設定.*", timeout=10)
                dlg = app.window(title_re=".*ファクス送信の設定.*")
                
                # 宛先番号入力（ハイフンを除去）
                self.emit_status('sending', f'FAX番号 {fax_number} を入力中...')
                clean_fax_number = fax_number.replace('-', '').replace(' ', '')
                
                edit_box = dlg.child_window(title_re=".*宛先番号.*", control_type="Edit")
                edit_box.set_focus()
                edit_box.type_keys(clean_fax_number, with_spaces=True)
                print(f"宛先番号 {clean_fax_number} を入力しました。")
                
                time.sleep(0.8)
                
                # 「送信開始」クリック
                self.emit_status('sending', 'FAX送信を開始中...')
                dlg.child_window(title="送信開始", control_type="Button").click_input()
                print("『送信開始』ボタンをクリックしました。")
                
                # 警告ダイアログを処理
                print("警告ウィンドウを探索中...")
                for i in range(10):  # 最大5秒間スキャン
                    warning_windows = [w for w in gw.getAllTitles() if "警告" in w]
                    if warning_windows:
                        print(f"警告ウィンドウ検出: {warning_windows[0]}")
                        win = gw.getWindowsWithTitle(warning_windows[0])[0]
                        win.activate()
                        time.sleep(0.5)
                        pyautogui.press("enter")  # OKを押す
                        print("『OK』を自動クリックしました。")
                        break
                    time.sleep(0.5)
                else:
                    print("⚠ 警告ダイアログが見つかりませんでした。")
                
                # ログに記録
                fax_logger.log_fax_complete(job_id, fax_number)
                
                self.emit_status('completed', f'FAX送信完了 (ジョブID: {job_id})', {
                    'job_id': job_id,
                    'fax_number': fax_number,
                    'completed_at': datetime.now().isoformat()
                })
                
            except Exception as e:
                raise Exception(f"FAXダイアログ操作エラー: {str(e)}")
                    
        except Exception as e:
            # エラーログに記録
            fax_logger.log_fax_error(job_id, str(e), fax_number)
            
            self.emit_status('error', f'FAX送信エラー: {str(e)}', {
                'job_id': job_id,
                'error': str(e)
            })
            raise
        
        finally:
            # 一時ファイルを削除
            if is_temp_file and file_path:
                try:
                    os.unlink(file_path)
                except:
                    pass
    
    def send_fax_async(self, fax_number, file_url, job_id=None):
        """非同期でFAX送信を実行"""
        def _send():
            try:
                self.send_fax(fax_number, file_url, job_id)
            except Exception as e:
                self.emit_status('error', f'非同期FAX送信エラー: {str(e)}')
        
        thread = threading.Thread(target=_send)
        thread.daemon = True
        thread.start()
        return thread
