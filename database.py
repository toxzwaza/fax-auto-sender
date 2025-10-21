import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class FaxDatabase:
    def __init__(self, db_path="fax_history.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """データベースとテーブルを初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # FAX送信履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fax_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                fax_number TEXT NOT NULL,
                file_url TEXT NOT NULL,
                callback_url TEXT,
                status TEXT NOT NULL DEFAULT 'queued',
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                processing_started_at TIMESTAMP
            )
        ''')
        
        # ステータス履歴テーブル
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES fax_history (job_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_fax_job(self, job_id: str, fax_number: str, file_url: str, callback_url: str = None) -> bool:
        """新しいFAX送信ジョブを作成（キューに追加）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO fax_history (job_id, fax_number, file_url, callback_url)
                VALUES (?, ?, ?, ?)
            ''', (job_id, fax_number, file_url, callback_url))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False  # ジョブIDが既に存在
        except Exception as e:
            print(f"データベースエラー: {e}")
            return False
    
    def update_fax_status(self, job_id: str, status: str, message: str = None, error_message: str = None) -> bool:
        """FAX送信ステータスを更新"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # メイン履歴を更新
            update_fields = ['status = ?', 'updated_at = CURRENT_TIMESTAMP']
            params = [status]
            
            if message:
                update_fields.append('message = ?')
                params.append(message)
            
            if error_message:
                update_fields.append('error_message = ?')
                params.append(error_message)
            
            if status == 'completed':
                update_fields.append('completed_at = CURRENT_TIMESTAMP')
            
            params.append(job_id)
            
            cursor.execute(f'''
                UPDATE fax_history 
                SET {', '.join(update_fields)}
                WHERE job_id = ?
            ''', params)
            
            # ステータス履歴に追加
            cursor.execute('''
                INSERT INTO status_history (job_id, status, message)
                VALUES (?, ?, ?)
            ''', (job_id, status, message))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"ステータス更新エラー: {e}")
            return False
    
    def get_fax_job(self, job_id: str) -> Optional[Dict]:
        """特定のFAX送信ジョブを取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM fax_history WHERE job_id = ?
            ''', (job_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_dict(row, cursor.description)
            return None
        except Exception as e:
            print(f"ジョブ取得エラー: {e}")
            return None
    
    def get_fax_history(self, limit: int = 100, offset: int = 0, status_filter: str = None) -> List[Dict]:
        """FAX送信履歴を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM fax_history 
            '''
            params = []
            
            if status_filter:
                query += ' WHERE status = ?'
                params.append(status_filter)
            
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_dict(row, cursor.description) for row in rows]
        except Exception as e:
            print(f"履歴取得エラー: {e}")
            return []
    
    def get_status_history(self, job_id: str) -> List[Dict]:
        """特定ジョブのステータス履歴を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM status_history 
                WHERE job_id = ? 
                ORDER BY timestamp ASC
            ''', (job_id,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_dict(row, cursor.description) for row in rows]
        except Exception as e:
            print(f"ステータス履歴取得エラー: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 総送信数
            cursor.execute('SELECT COUNT(*) FROM fax_history')
            total_count = cursor.fetchone()[0]
            
            # ステータス別集計
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM fax_history 
                GROUP BY status
            ''')
            status_counts = dict(cursor.fetchall())
            
            # 今日の送信数
            cursor.execute('''
                SELECT COUNT(*) 
                FROM fax_history 
                WHERE DATE(created_at) = DATE('now')
            ''')
            today_count = cursor.fetchone()[0]
            
            # 今月の送信数
            cursor.execute('''
                SELECT COUNT(*) 
                FROM fax_history 
                WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            ''')
            month_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_count': total_count,
                'today_count': today_count,
                'month_count': month_count,
                'status_counts': status_counts
            }
        except Exception as e:
            print(f"統計取得エラー: {e}")
            return {}
    
    def increment_retry_count(self, job_id: str) -> bool:
        """リトライ回数を増加"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE fax_history 
                SET retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            ''', (job_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"リトライ回数更新エラー: {e}")
            return False
    
    def get_next_job(self) -> Optional[Dict]:
        """次の処理対象ジョブを取得（作成日時順）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM fax_history 
                WHERE status = 'queued' 
                ORDER BY created_at ASC 
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_dict(row, cursor.description)
            return None
        except Exception as e:
            print(f"次のジョブ取得エラー: {e}")
            return None
    
    def mark_job_processing(self, job_id: str) -> bool:
        """ジョブを処理中にマーク"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE fax_history 
                SET status = 'processing', 
                    processing_started_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            ''', (job_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"ジョブ処理中マークエラー: {e}")
            return False
    
    def get_queue_status(self) -> Dict:
        """キュー状況を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # キュー内のジョブ数
            cursor.execute('SELECT COUNT(*) FROM fax_history WHERE status = "queued"')
            queued_count = cursor.fetchone()[0]
            
            # 処理中のジョブ数
            cursor.execute('SELECT COUNT(*) FROM fax_history WHERE status = "processing"')
            processing_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'queued_count': queued_count,
                'processing_count': processing_count
            }
        except Exception as e:
            print(f"キュー状況取得エラー: {e}")
            return {}
    
    def _row_to_dict(self, row, description):
        """データベース行を辞書に変換"""
        return {description[i][0]: row[i] for i in range(len(row))}
