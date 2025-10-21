import win32print
import win32api
import os
import requests
import tempfile
import threading
from datetime import datetime
import json
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
        """FAX送信を実行"""
        if job_id is None:
            job_id = f"fax_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
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
            
            try:
                # プリンタハンドルを取得
                self.emit_status('connecting', 'FAXドライバーに接続中...')
                printer = win32print.OpenPrinter(self.printer_name)
                
                try:
                    # 印刷ジョブを開始
                    self.emit_status('printing', '印刷ジョブを開始中...')
                    hJob = win32print.StartDocPrinter(printer, 1, (f"FAX送信_{job_id}", None, "RAW"))
                    win32print.StartPagePrinter(printer)

                    # ファイルを送信
                    self.emit_status('sending', f'FAX番号 {fax_number} に送信中...')
                    with open(file_path, "rb") as f:
                        win32print.WritePrinter(printer, f.read())

                    win32print.EndPagePrinter(printer)
                    win32print.EndDocPrinter(printer)
                    
                    # ログに記録
                    fax_logger.log_fax_complete(job_id, fax_number)
                    
                    self.emit_status('completed', f'FAX送信完了 (ジョブID: {job_id})', {
                        'job_id': job_id,
                        'fax_number': fax_number,
                        'completed_at': datetime.now().isoformat()
                    })
                    
                finally:
                    win32print.ClosePrinter(printer)
                    
            finally:
                # 一時ファイルを削除
                try:
                    os.unlink(file_path)
                except:
                    pass
                    
        except Exception as e:
            # エラーログに記録
            fax_logger.log_fax_error(job_id, str(e), fax_number)
            
            self.emit_status('error', f'FAX送信エラー: {str(e)}', {
                'job_id': job_id,
                'error': str(e)
            })
            raise
    
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
