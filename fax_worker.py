import threading
import time
from datetime import datetime
from fax_service import FaxService
from database import FaxDatabase
from callback_service import CallbackService
from logger import fax_logger

class FaxWorker:
    def __init__(self, db: FaxDatabase, fax_service: FaxService, interval: int = 5):
        """
        FAX送信ワーカー
        
        Args:
            db: データベースインスタンス
            fax_service: FAX送信サービスインスタンス
            interval: チェック間隔（秒）
        """
        self.db = db
        self.fax_service = fax_service
        self.callback_service = CallbackService()
        self.interval = interval
        self.running = False
        self.worker_thread = None
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
    
    def start(self):
        """ワーカーを開始"""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        print(f"FAX送信ワーカーを開始しました（チェック間隔: {self.interval}秒）")
    
    def stop(self):
        """ワーカーを停止"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join()
        print("FAX送信ワーカーを停止しました")
    
    def _worker_loop(self):
        """ワーカーのメインループ"""
        while self.running:
            try:
                self._process_next_job()
            except Exception as e:
                print(f"ワーカーループエラー: {e}")
                fax_logger.log_system_error(f"ワーカーループエラー: {e}")
            
            time.sleep(self.interval)
    
    def _process_next_job(self):
        """次のジョブを処理"""
        # 次の処理対象ジョブを取得
        job = self.db.get_next_job()
        if not job:
            return
        
        job_id = job['job_id']
        fax_number = job['fax_number']
        file_url = job['file_url']
        callback_url = job.get('callback_url')
        
        try:
            # ジョブを処理中にマーク
            if not self.db.mark_job_processing(job_id):
                print(f"ジョブ {job_id} の処理中マークに失敗")
                return
            
            # ステータスを更新
            self.db.update_fax_status(job_id, 'processing', 'FAX送信処理を開始しました')
            self.emit_status('processing', f'FAX送信処理を開始しました (ジョブID: {job_id})', {
                'job_id': job_id,
                'fax_number': fax_number
            })
            
            # ログに記録
            fax_logger.log_fax_start(job_id, fax_number, file_url)
            
            # FAX送信を実行
            self.fax_service.send_fax(fax_number, file_url, job_id)
            
            # 完了ステータスを更新
            self.db.update_fax_status(job_id, 'completed', 'FAX送信が完了しました')
            self.emit_status('completed', f'FAX送信が完了しました (ジョブID: {job_id})', {
                'job_id': job_id,
                'fax_number': fax_number,
                'completed_at': datetime.now().isoformat()
            })
            
            # ログに記録
            fax_logger.log_fax_complete(job_id, fax_number)
            
            # コールバック送信
            if callback_url:
                self.callback_service.send_callback_async(
                    callback_url, job_id, 'completed', 'FAX送信が完了しました'
                )
            
        except Exception as e:
            error_message = str(e)
            print(f"ジョブ {job_id} の処理エラー: {error_message}")
            
            # エラーステータスを更新
            self.db.update_fax_status(job_id, 'error', f'FAX送信エラー: {error_message}', error_message)
            self.emit_status('error', f'FAX送信エラー: {error_message}', {
                'job_id': job_id,
                'error': error_message
            })
            
            # エラーログに記録
            fax_logger.log_fax_error(job_id, error_message, fax_number)
            
            # エラー時のコールバック送信
            if callback_url:
                self.callback_service.send_callback_async(
                    callback_url, job_id, 'error', f'FAX送信エラー: {error_message}', error_message
                )
    
    def get_queue_status(self):
        """キュー状況を取得"""
        return self.db.get_queue_status()
    
    def is_running(self):
        """ワーカーが実行中かどうか"""
        return self.running
