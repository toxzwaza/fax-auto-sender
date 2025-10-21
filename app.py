from flask import Flask, request, jsonify
import requests
import os
import json
import time
import threading
import uuid
from datetime import datetime
from fax_sender import send_fax_with_retry, cleanup_temp_files

app = Flask(__name__)

# 設定
PARAMETER_FILE = "parameter.json"

# グローバルロックを定義（FAX送信中の並列実行を防止）
fax_lock = threading.Lock()

# -------------------------------
# JSONデータ操作
# -------------------------------

def load_parameters():
    """parameter.jsonからデータを読み込み"""
    try:
        if not os.path.exists(PARAMETER_FILE):
            return []
        if os.path.getsize(PARAMETER_FILE) == 0:
            print("⚠ parameter.jsonが空のため初期化します。")
            return []

        with open(PARAMETER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                print("古い形式のparameter.jsonを検出。新しい形式に変換します。")
                return []
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"パラメータ読み込みエラー: {e}")
        return []

def save_parameters(data):
    """parameter.jsonにデータを保存"""
    try:
        with open(PARAMETER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"パラメータ保存エラー: {e}")

def add_fax_request(file_url, fax_number):
    """新しいFAX送信リクエストを追加"""
    params_list = load_parameters()
    
    new_request = {
        "id": str(uuid.uuid4()),
        "file_url": file_url,
        "fax_number": fax_number,
        "status": 0,  # 0: 待機中, 1: 完了, -1: エラー, 2: 処理中
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error_message": None
    }
    
    params_list.append(new_request)
    save_parameters(params_list)
    
    return new_request

def update_request_status(request_id, status, error_message=None):
    """リクエストのステータスを更新"""
    params_list = load_parameters()
    
    if not isinstance(params_list, list):
        print(f"パラメータデータが配列ではありません: {type(params_list)}")
        return
    
    for request in params_list:
        if isinstance(request, dict) and request.get("id") == request_id:
            request["status"] = status
            request["updated_at"] = datetime.now().isoformat()
            if error_message:
                request["error_message"] = error_message
            break
    
    save_parameters(params_list)

# -------------------------------
# ファイル処理
# -------------------------------

def download_file(file_url, local_path):
    """ファイルをダウンロードまたはローカルコピー"""
    try:
        if file_url.startswith('file://'):
            local_file_path = file_url[7:]
            if local_file_path.startswith('/'):
                local_file_path = local_file_path[1:]
            if not os.path.exists(local_file_path):
                print(f"ローカルファイルが見つかりません: {local_file_path}")
                return False
            import shutil
            shutil.copy2(local_file_path, local_path)
            print(f"ローカルファイルをコピーしました: {local_file_path} -> {local_path}")
            return True
        else:
            response = requests.get(file_url)
            response.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(response.content)
            print(f"リモートファイルをダウンロードしました: {file_url}")
            return True
    except Exception as e:
        print(f"ファイル処理エラー: {e}")
        return False

# -------------------------------
# FAX送信処理
# -------------------------------

def process_single_fax_request(request_data):
    """単一のFAX送信リクエストを処理"""
    request_id = request_data["id"]
    file_url = request_data["file_url"]
    fax_number = request_data["fax_number"]
    print(f"FAX送信処理開始: ID={request_id}, FAX番号={fax_number}")

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_file_path = f"temp_fax_{timestamp}.pdf"

        if not download_file(file_url, local_file_path):
            update_request_status(request_id, -1, f"ファイル取得に失敗: {file_url}")
            return False

        # FAX送信実行（リトライ機能付き）
        if send_fax_with_retry(os.path.abspath(local_file_path), fax_number):
            update_request_status(request_id, 1)
            print(f"FAX送信完了: ID={request_id}")
            return True
        else:
            update_request_status(request_id, -1, "FAX送信に失敗しました")
            print(f"FAX送信失敗: ID={request_id}")
            return False

    except Exception as e:
        update_request_status(request_id, -1, str(e))
        print(f"FAX送信処理エラー: {e}")
        return False

    finally:
        try:
            os.remove(local_file_path)
        except:
            pass

# -------------------------------
# ワーカースレッド
# -------------------------------

def fax_worker():
    """FAX送信ワーカー（順次処理）"""
    print("FAX送信ワーカー開始（排他制御あり）")
    while True:
        try:
            params_list = load_parameters()
            if not isinstance(params_list, list):
                time.sleep(5)
                continue

            pending = [p for p in params_list if p.get("status") == 0]
            if pending:
                request_data = pending[0]
                request_id = request_data["id"]
                update_request_status(request_id, 2, "処理中")

                # 🔒 ロックでワーカー全体を排他制御
                with fax_lock:
                    process_single_fax_request(request_data)

                time.sleep(1)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"FAXワーカーエラー: {e}")
            time.sleep(5)

# -------------------------------
# Flask API
# -------------------------------

@app.route('/send_fax', methods=['POST'])
def send_fax_api():
    """FAX送信API"""
    try:
        data = request.get_json()
        file_url = data.get('file_url')
        fax_number = data.get('fax_number')

        if not file_url or not fax_number:
            return jsonify({'success': False, 'error': 'file_urlとfax_numberは必須です'}), 400

        new_request = add_fax_request(file_url, fax_number)
        return jsonify({
            'success': True,
            'message': 'FAX送信リクエストを登録しました',
            'request_id': new_request['id'],
            'status': 'pending'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/status/<request_id>', methods=['GET'])
def get_request_status(request_id):
    """ステータス確認"""
    params_list = load_parameters()
    for r in params_list:
        if r.get("id") == request_id:
            return jsonify({'success': True, 'request': r})
    return jsonify({'success': False, 'error': '該当リクエストなし'}), 404

@app.route('/requests', methods=['GET'])
def get_all_requests():
    """全リクエスト一覧"""
    params_list = load_parameters()
    return jsonify({'success': True, 'requests': params_list, 'total': len(params_list)})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# -------------------------------
# メイン処理
# -------------------------------

if __name__ == '__main__':
    worker_thread = threading.Thread(target=fax_worker, daemon=True)
    worker_thread.start()
    print("FAX送信APIサーバー起動中...")
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
