import requests
import threading
from datetime import datetime
from logger import fax_logger

class CallbackService:
    def __init__(self):
        self.callback_timeout = 10  # コールバックタイムアウト（秒）
    
    def send_callback(self, callback_url: str, job_id: str, status: str, message: str = None, error_message: str = None):
        """コールバックURLにGETリクエストを送信"""
        if not callback_url:
            return
        
        try:
            # コールバックパラメータを構築
            params = {
                'job_id': job_id,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
            
            if message:
                params['message'] = message
            
            if error_message:
                params['error_message'] = error_message
            
            # GETリクエストでコールバックを送信
            response = requests.get(
                callback_url, 
                params=params, 
                timeout=self.callback_timeout
            )
            
            if response.status_code == 200:
                fax_logger.log_system_error(f"コールバック送信成功: {callback_url} (ジョブID: {job_id})")
            else:
                fax_logger.log_system_error(f"コールバック送信失敗: {callback_url} (ステータス: {response.status_code})")
                
        except requests.exceptions.Timeout:
            fax_logger.log_system_error(f"コールバック送信タイムアウト: {callback_url}")
        except requests.exceptions.RequestException as e:
            fax_logger.log_system_error(f"コールバック送信エラー: {callback_url} - {str(e)}")
        except Exception as e:
            fax_logger.log_system_error(f"コールバック送信予期しないエラー: {callback_url} - {str(e)}")
    
    def send_callback_async(self, callback_url: str, job_id: str, status: str, message: str = None, error_message: str = None):
        """非同期でコールバックを送信"""
        def _send():
            self.send_callback(callback_url, job_id, status, message, error_message)
        
        thread = threading.Thread(target=_send)
        thread.daemon = True
        thread.start()
        return thread


