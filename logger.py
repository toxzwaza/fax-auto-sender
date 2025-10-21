import logging
import os
from datetime import datetime

class FaxLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定を初期化"""
        # ログディレクトリを作成
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # ログファイル名（日付別）
        log_filename = os.path.join(self.log_dir, f"fax_{datetime.now().strftime('%Y%m%d')}.log")
        
        # ログ設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()  # コンソール出力も有効
            ]
        )
        
        self.logger = logging.getLogger('FaxService')
    
    def log_fax_start(self, job_id, fax_number, pdf_url):
        """FAX送信開始をログ"""
        self.logger.info(f"FAX送信開始 - JobID: {job_id}, FAX: {fax_number}, URL: {pdf_url}")
    
    def log_fax_status(self, job_id, status, message):
        """FAX送信ステータスをログ"""
        self.logger.info(f"FAX送信ステータス - JobID: {job_id}, Status: {status}, Message: {message}")
    
    def log_fax_complete(self, job_id, fax_number):
        """FAX送信完了をログ"""
        self.logger.info(f"FAX送信完了 - JobID: {job_id}, FAX: {fax_number}")
    
    def log_fax_error(self, job_id, error_message, fax_number=None):
        """FAX送信エラーをログ"""
        self.logger.error(f"FAX送信エラー - JobID: {job_id}, Error: {error_message}, FAX: {fax_number}")
    
    def log_system_error(self, error_message):
        """システムエラーをログ"""
        self.logger.error(f"システムエラー - {error_message}")

# グローバルロガーインスタンス
fax_logger = FaxLogger()

