from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import uuid
from fax_service import FaxService
from database import FaxDatabase
from fax_worker import FaxWorker
import threading
import time
import hashlib
import hmac
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fax_auto_sender_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# FAXサービスのインスタンス
fax_service = FaxService()

# データベースのインスタンス
db = FaxDatabase()

# FAX送信ワーカーのインスタンス
fax_worker = FaxWorker(db, fax_service, interval=5)

# API認証用のシークレットキー（環境変数から取得、デフォルト値あり）
API_SECRET_KEY = os.getenv('FAX_API_SECRET', 'default_secret_key_change_in_production')

def verify_api_key():
    """API認証を検証"""
    api_key = request.headers.get('X-API-Key')
    if not api_key:
        return False
    
    # シンプルなAPIキー認証（本番環境ではより堅牢な認証を推奨）
    return api_key == API_SECRET_KEY

def require_auth(f):
    """認証が必要なエンドポイント用デコレータ"""
    def decorated_function(*args, **kwargs):
        if not verify_api_key():
            return jsonify({'error': '認証が必要です'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """管理画面"""
    return render_template('admin.html')

@app.route('/api/send_fax', methods=['POST'])
@require_auth
def send_fax():
    """LaravelアプリからのFAX送信API"""
    try:
        data = request.get_json()
        fax_number = data.get('fax_number')
        file_url = data.get('file_url')
        callback_url = data.get('callback_url')
        
        if not fax_number or not file_url:
            return jsonify({'error': 'FAX番号とファイルURLが必要です'}), 400
        
        # ジョブIDを生成
        job_id = str(uuid.uuid4())
        
        # データベースにジョブを作成（キューに追加）
        if not db.create_fax_job(job_id, fax_number, file_url, callback_url):
            return jsonify({'error': 'ジョブの作成に失敗しました'}), 500
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'FAX送信をキューに追加しました',
            'status': 'queued'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/send_fax_web', methods=['POST'])
def send_fax_web():
    """Web UIからのFAX送信API（認証不要）"""
    try:
        data = request.get_json()
        fax_number = data.get('fax_number')
        file_url = data.get('file_url')
        callback_url = data.get('callback_url')
        
        if not fax_number or not file_url:
            return jsonify({'error': 'FAX番号とファイルURLが必要です'}), 400
        
        # ジョブIDを生成
        job_id = str(uuid.uuid4())
        
        # データベースにジョブを作成（キューに追加）
        if not db.create_fax_job(job_id, fax_number, file_url, callback_url):
            return jsonify({'error': 'ジョブの作成に失敗しました'}), 500
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'FAX送信をキューに追加しました',
            'status': 'queued'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test_send', methods=['POST'])
def test_send():
    """テスト送信API"""
    try:
        # テスト用のジョブIDを生成
        job_id = str(uuid.uuid4())
        
        # テスト用のファイルパスを取得
        import os
        test_file_path = os.path.abspath("fax_test.pdf")
        
        # ファイルの存在確認
        if not os.path.exists(test_file_path):
            return jsonify({'error': f'テストファイルが見つかりません: {test_file_path}'}), 500
        
        # ローカルファイルのURLを作成（実際の環境では適切なURLに変更）
        file_url = f"file:///{test_file_path.replace(os.sep, '/')}"
        
        print(f"テスト送信: job_id={job_id}, file_path={test_file_path}, file_url={file_url}")
        
        # データベースにジョブを作成
        if not db.create_fax_job(job_id, "043-211-9261", file_url, "https://akioka.cloud/calback_url/test"):
            return jsonify({'error': 'テストジョブの作成に失敗しました'}), 500
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'テスト送信をキューに追加しました',
            'status': 'queued',
            'fax_number': '043-211-9261',
            'file_url': file_url,
            'callback_url': 'https://akioka.cloud/calback_url/test'
        })
        
    except Exception as e:
        print(f"テスト送信エラー: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/job_status/<job_id>')
def get_job_status(job_id):
    """ジョブステータス取得API"""
    job = db.get_fax_job(job_id)
    if job:
        return jsonify(job)
    else:
        return jsonify({'error': 'ジョブが見つかりません'}), 404

@app.route('/api/jobs')
def get_all_jobs():
    """全ジョブ一覧取得API"""
    jobs = db.get_fax_history(limit=100)
    return jsonify(jobs)

@app.route('/api/admin/history')
def get_admin_history():
    """管理画面用：FAX送信履歴取得API"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        status_filter = request.args.get('status')
        
        offset = (page - 1) * per_page
        jobs = db.get_fax_history(limit=per_page, offset=offset, status_filter=status_filter)
        
        return jsonify({
            'jobs': jobs,
            'page': page,
            'per_page': per_page,
            'total': len(jobs)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/statistics')
def get_admin_statistics():
    """管理画面用：統計情報取得API"""
    try:
        stats = db.get_statistics()
        queue_status = fax_worker.get_queue_status()
        stats.update(queue_status)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/queue_status')
def get_queue_status():
    """キュー状況取得API"""
    try:
        queue_status = fax_worker.get_queue_status()
        return jsonify(queue_status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/job/<job_id>/status_history')
def get_job_status_history(job_id):
    """管理画面用：ジョブのステータス履歴取得API"""
    try:
        history = db.get_status_history(job_id)
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/job/<job_id>/retry', methods=['POST'])
@require_auth
def retry_job(job_id):
    """管理画面用：ジョブの再試行API"""
    try:
        job = db.get_fax_job(job_id)
        if not job:
            return jsonify({'error': 'ジョブが見つかりません'}), 404
        
        if job['status'] not in ['error', 'failed']:
            return jsonify({'error': '再試行可能なステータスではありません'}), 400
        
        # リトライ回数を増加
        db.increment_retry_count(job_id)
        
        # ジョブをキューに再追加
        db.create_fax_job(job_id, job['fax_number'], job['file_url'], job.get('callback_url'))
        
        return jsonify({
            'success': True,
            'message': 'ジョブの再試行を開始しました'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """WebSocket接続時の処理"""
    print(f'クライアントが接続しました: {request.sid}')
    emit('connected', {'message': 'FAX送信サーバーに接続しました'})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket切断時の処理"""
    print(f'クライアントが切断しました: {request.sid}')

@socketio.on('join_job')
def handle_join_job(data):
    """特定のジョブの監視に参加"""
    job_id = data.get('job_id')
    if job_id:
        join_room(f'job_{job_id}')
        emit('joined_job', {'job_id': job_id, 'message': f'ジョブ {job_id} の監視を開始しました'})

@socketio.on('leave_job')
def handle_leave_job(data):
    """ジョブの監視から退出"""
    job_id = data.get('job_id')
    if job_id:
        leave_room(f'job_{job_id}')
        emit('left_job', {'job_id': job_id, 'message': f'ジョブ {job_id} の監視を終了しました'})

def update_job_status(status_data):
    """ジョブステータスを更新してWebSocketで通知"""
    job_id = status_data.get('data', {}).get('job_id')
    
    if job_id:
        # データベースのステータスを更新
        db.update_fax_status(
            job_id, 
            status_data['status'], 
            status_data['message'],
            status_data.get('error')
        )
        
        # WebSocketで通知
        socketio.emit('job_update', status_data, room=f'job_{job_id}')
        socketio.emit('job_update', status_data)  # 全クライアントにも通知
    
    # ログ出力
    print(f"[{status_data['timestamp']}] {status_data['status']}: {status_data['message']}")

# FAXサービスのコールバックを設定
fax_service.add_status_callback(update_job_status)

# FAXワーカーのコールバックを設定
fax_worker.add_status_callback(update_job_status)

if __name__ == '__main__':
    print("FAX自動送信Webアプリケーションを起動中...")
    print("ブラウザで http://localhost:5000 にアクセスしてください")
    
    # FAX送信ワーカーを開始
    fax_worker.start()
    
    try:
        socketio.run(app, debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nFAX送信ワーカーを停止中...")
        fax_worker.stop()
        print("アプリケーションを終了しました")
