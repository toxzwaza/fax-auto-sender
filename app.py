from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import os
import json
import time
import threading
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from fax_sender import send_fax_with_retry, cleanup_temp_files
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image

app = Flask(__name__)
CORS(app) # すべてのオリジンを許可
# CORS(app, resources={r"/send_fax": {"origins": "http://monokanri-manage.local"}})
# CORS(app, resources={r"/send_fax": {"origins": "http://127.0.0.1:8000"}})

# 設定
PARAMETER_FILE = "parameter.json"
UPLOAD_FOLDER = "uploads"
CONVERTED_PDF_FOLDER = "converted_pdfs"
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'tiff', 'tif'}

# フォルダを作成
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(CONVERTED_PDF_FOLDER):
    os.makedirs(CONVERTED_PDF_FOLDER)

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

def add_fax_request(file_url, fax_number, request_user=None, file_name=None, callback_url=None, order_destination=None):
    """新しいFAX送信リクエストを追加"""
    params_list = load_parameters()
    
    new_request = {
        "id": str(uuid.uuid4()),
        "file_url": file_url,
        "fax_number": fax_number,
        "status": 0,  # 0: 待機中, 1: 完了, -1: エラー, 2: 処理中
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "error_message": None,
        "converted_pdf_path": None,  # PDF変換後のファイルパス
        "request_user": request_user,  # 依頼者名
        "file_name": file_name,  # ファイル名
        "callback_url": callback_url,  # 通知先URL
        "order_destination": order_destination  # 発注先
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

def update_request_converted_pdf(request_id, pdf_path):
    """リクエストの変換後PDFファイルパスを更新"""
    params_list = load_parameters()
    
    if not isinstance(params_list, list):
        print(f"パラメータデータが配列ではありません: {type(params_list)}")
        return
    
    for request in params_list:
        if isinstance(request, dict) and request.get("id") == request_id:
            request["converted_pdf_path"] = pdf_path
            request["updated_at"] = datetime.now().isoformat()
            break
    
    save_parameters(params_list)

def try_regenerate_converted_pdf(request_id, request_data):
    """変換されたPDFファイルを再生成"""
    try:
        file_url = request_data.get("file_url")
        if not file_url:
            return jsonify({'success': False, 'error': '元ファイルのURLがありません'}), 404
        
        # 元ファイルがPDFの場合は変換不要
        if file_url.lower().endswith(".pdf"):
            return jsonify({'success': False, 'error': '元ファイルがPDFのため変換は不要です'}), 400
        
        # 元ファイルをダウンロード
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file_path = f"temp_regen_{timestamp}"
        
        # ファイル拡張子を決定
        temp_ext = ".tmp"
        if file_url.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.tif')):
            temp_ext = os.path.splitext(file_url)[1]
        
        temp_path = temp_file_path + temp_ext
        
        if not download_file(file_url, temp_path):
            return jsonify({'success': False, 'error': '元ファイルの取得に失敗しました'}), 404
        
        # 永続フォルダに変換されたPDFを保存
        persistent_pdf_name = f"converted_{request_id}_{timestamp}.pdf"
        persistent_pdf_path = os.path.join(CONVERTED_PDF_FOLDER, persistent_pdf_name)
        
        # PDFに変換
        create_pdf_from_image(temp_path, persistent_pdf_path)
        
        # 一時ファイルを削除
        os.remove(temp_path)
        
        # データベースを更新
        update_request_converted_pdf(request_id, os.path.abspath(persistent_pdf_path))
        
        # PDFファイルを返す
        with open(persistent_pdf_path, 'rb') as f:
            file_content = f.read()
        
        from flask import Response
        return Response(file_content, mimetype='application/pdf')
        
    except Exception as e:
        print(f"PDF再生成エラー: {e}")
        return jsonify({'success': False, 'error': f'PDF再生成に失敗しました: {str(e)}'}), 500

# -------------------------------
# ファイル処理
# -------------------------------

def allowed_file(filename):
    """ファイル拡張子をチェック"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """アップロードされたファイルを保存"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # タイムスタンプを追加してファイル名の重複を避ける
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{timestamp}{ext}"
        
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        print(f"ファイルをアップロードしました: {file_path}")
        return file_path
    return None

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
# PDF作成処理
# -------------------------------
def create_pdf_from_image(image_path, output_pdf_path):
    """画像をA4縦のPDFに貼り付けて保存（余白最小化）"""
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

    img = Image.open(image_path)
    img_width, img_height = img.size
    aspect = img_height / img_width

    # A4余白を最小限（3mm程度）に設定
    margin = 6  # 3mm程度の最小余白
    max_width = width - (margin * 2)
    max_height = height - (margin * 2)
    
    # A4のアスペクト比（縦長）
    a4_aspect = height / width
    
    # 画像のアスペクト比とA4のアスペクト比を比較して最適な配置を決定
    if aspect > a4_aspect:
        # 画像が縦長の場合：高さを基準にサイズを決定
        display_height = max_height
        display_width = max_height / aspect
    else:
        # 画像が横長または正方形の場合：幅を基準にサイズを決定
        display_width = max_width
        display_height = max_width * aspect

    # 中央配置
    x = (width - display_width) / 2
    y = (height - display_height) / 2
    
    # 画像を描画
    c.drawImage(ImageReader(img), x, y, display_width, display_height)
    c.showPage()
    c.save()
    print(f"画像をA4 PDFに変換しました（余白最小化・最適化）: {output_pdf_path}")
    print(f"  元画像サイズ: {img_width}x{img_height}, アスペクト比: {aspect:.3f}")
    print(f"  表示サイズ: {display_width:.1f}x{display_height:.1f}, 余白: {margin}pt")

# -------------------------------
# コールバック通知
# -------------------------------

def send_callback_notification(request_data):
    """コールバックURLにGET通知を送信（成功時のみ）"""
    callback_url = request_data.get("callback_url")
    if not callback_url:
        return  # callback_urlが設定されていない場合は何もしない
    
    try:
        # コールバックURLにGETリクエストを送信（パラメータなし）
        print(f"📞 コールバック通知送信: {callback_url}")
        response = requests.get(callback_url, timeout=10)
        response.raise_for_status()
        print(f"✅ コールバック通知成功: ステータスコード={response.status_code}")
        
    except requests.exceptions.Timeout:
        print(f"⚠ コールバック通知タイムアウト: {callback_url}")
    except requests.exceptions.RequestException as e:
        print(f"⚠ コールバック通知エラー: {e}")
    except Exception as e:
        print(f"⚠ コールバック通知処理エラー: {e}")

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
        local_file_path = f"temp_fax_{timestamp}"

        # 元ファイルをダウンロード
        temp_ext = ".pdf" if file_url.lower().endswith(".pdf") else ".tmp"
        temp_path = local_file_path + temp_ext
        if not download_file(file_url, temp_path):
            update_request_status(request_id, -1, f"ファイル取得に失敗: {file_url}")
            return False

        # 🟡 PDF以外の場合はPDFに変換
        if not file_url.lower().endswith(".pdf"):
            # 永続フォルダに変換されたPDFを保存
            persistent_pdf_name = f"converted_{request_id}_{timestamp}.pdf"
            persistent_pdf_path = os.path.join(CONVERTED_PDF_FOLDER, persistent_pdf_name)
            
            # 一時PDFを作成
            temp_pdf_path = local_file_path + ".pdf"
            create_pdf_from_image(temp_path, temp_pdf_path)
            os.remove(temp_path)
            
            # 永続フォルダにコピー
            import shutil
            shutil.copy2(temp_pdf_path, persistent_pdf_path)
            
            send_path = temp_pdf_path
            
            # 変換後のPDFファイルパスを保存
            update_request_converted_pdf(request_id, os.path.abspath(persistent_pdf_path))
        else:
            send_path = temp_path

        # FAX送信実行
        if send_fax_with_retry(os.path.abspath(send_path), fax_number):
            update_request_status(request_id, 1)
            print(f"FAX送信完了: ID={request_id}")
            # コールバック通知を送信（成功時のみ）
            send_callback_notification(request_data)
            return True
        else:
            error_msg = "FAX送信に失敗しました"
            update_request_status(request_id, -1, error_msg)
            print(f"FAX送信失敗: ID={request_id}")
            return False

    except Exception as e:
        error_msg = str(e)
        update_request_status(request_id, -1, error_msg)
        print(f"FAX送信処理エラー: {e}")
        return False

    finally:
        # FAXドライバーがファイルを使用中の場合があるため、削除をリトライ
        for f in [local_file_path + ".pdf", local_file_path + ".tmp"]:
            if os.path.exists(f):
                for retry in range(5):
                    try:
                        os.remove(f)
                        print(f"一時ファイルを削除: {f}")
                        break
                    except PermissionError:
                        print(f"⚠ ファイル使用中のため削除保留: {f} (試行 {retry+1}/5)")
                        time.sleep(2)
                else:
                    print(f"⚠ ファイル削除失敗（使用中の可能性あり）: {f}")


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
    """FAX送信API（URL指定）"""
    try:
        data = request.get_json()
        file_url = data.get('file_url')
        fax_number = data.get('fax_number')
        request_user = data.get('request_user')  # オプション
        file_name = data.get('file_name')  # オプション
        callback_url = data.get('callback_url')  # オプション
        order_destination = data.get('order_destination')  # オプション

        if not file_url or not fax_number:
            return jsonify({'success': False, 'error': 'file_urlとfax_numberは必須です'}), 400

        new_request = add_fax_request(file_url, fax_number, request_user, file_name, callback_url, order_destination)
        return jsonify({
            'success': True,
            'message': 'FAX送信リクエストを登録しました',
            'request_id': new_request['id'],  # 後方互換性のため
            'status': 'pending',
            'request_user': new_request.get('request_user'),
            'file_name': new_request.get('file_name'),
            'callback_url': new_request.get('callback_url'),
            'order_destination': new_request.get('order_destination'),
            'fax_number': new_request['fax_number'],
            'created_at': new_request['created_at']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/upload_and_send_fax', methods=['POST'])
def upload_and_send_fax():
    """ファイルアップロード＆FAX送信API"""
    try:
        # ファイルの確認
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400
        
        file = request.files['file']
        fax_number = request.form.get('fax_number')
        request_user = request.form.get('request_user')  # オプション
        file_name = request.form.get('file_name')  # オプション
        callback_url = request.form.get('callback_url')  # オプション
        order_destination = request.form.get('order_destination')  # オプション
        
        if not fax_number:
            return jsonify({'success': False, 'error': 'fax_numberは必須です'}), 400
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400
        
        # ファイルを保存
        file_path = save_uploaded_file(file)
        if not file_path:
            return jsonify({'success': False, 'error': 'サポートされていないファイル形式です'}), 400
        
        # ファイル名が指定されていない場合は、アップロードされたファイル名を使用
        if not file_name:
            file_name = file.filename
        
        # ローカルファイルURLとして登録
        file_url = f"file:///{file_path.replace(os.sep, '/')}"
        new_request = add_fax_request(file_url, fax_number, request_user, file_name, callback_url, order_destination)
        
        return jsonify({
            'success': True,
            'message': 'ファイルをアップロードし、FAX送信リクエストを登録しました',
            'id': new_request['id'],
            'status': 'pending',
            'request_user': new_request.get('request_user'),
            'file_name': new_request.get('file_name'),
            'callback_url': new_request.get('callback_url'),
            'order_destination': new_request.get('order_destination'),
            'fax_number': new_request['fax_number'],
            'uploaded_file': file_path,
            'created_at': new_request['created_at']
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

@app.route('/', methods=['GET'])
def admin():
    """管理画面を表示"""
    return render_template('admin.html')

@app.route('/clear_completed', methods=['POST'])
def clear_completed():
    """完了済みの送信履歴を削除"""
    try:
        params_list = load_parameters()
        if not isinstance(params_list, list):
            return jsonify({'success': False, 'error': 'パラメータデータが配列ではありません'}), 400
        
        # 完了済み（status=1）のリクエストを除外
        filtered_list = [r for r in params_list if r.get("status") != 1]
        deleted_count = len(params_list) - len(filtered_list)
        
        save_parameters(filtered_list)
        
        return jsonify({
            'success': True, 
            'message': f'{deleted_count}件の完了済み送信履歴を削除しました',
            'deleted_count': deleted_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/retry_errors', methods=['POST'])
def retry_errors():
    """エラー状態の送信を再送"""
    try:
        params_list = load_parameters()
        if not isinstance(params_list, list):
            return jsonify({'success': False, 'error': 'パラメータデータが配列ではありません'}), 400
        
        # エラー状態（status=-1）のリクエストを待機中（status=0）に変更
        retry_count = 0
        for request in params_list:
            if request.get("status") == -1:
                request["status"] = 0
                request["updated_at"] = datetime.now().isoformat()
                request["error_message"] = None
                retry_count += 1
        
        save_parameters(params_list)
        
        return jsonify({
            'success': True, 
            'message': f'{retry_count}件のエラー送信を再送しました',
            'retry_count': retry_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/retry_request/<request_id>', methods=['POST'])
def retry_request(request_id):
    """個別の送信を再送"""
    try:
        params_list = load_parameters()
        if not isinstance(params_list, list):
            return jsonify({'success': False, 'error': 'パラメータデータが配列ではありません'}), 400
        
        # 指定されたIDのリクエストを探して再送
        for request in params_list:
            if request.get("id") == request_id:
                if request.get("status") == -1:  # エラー状態の場合のみ
                    request["status"] = 0
                    request["updated_at"] = datetime.now().isoformat()
                    request["error_message"] = None
                    save_parameters(params_list)
                    return jsonify({'success': True, 'message': '送信を再送しました'})
                else:
                    return jsonify({'success': False, 'error': 'エラー状態の送信のみ再送可能です'}), 400
        
        return jsonify({'success': False, 'error': '該当する送信が見つかりません'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear_all', methods=['POST'])
def clear_all():
    """すべての送信履歴を削除"""
    try:
        params_list = load_parameters()
        total_count = len(params_list) if isinstance(params_list, list) else 0
        
        save_parameters([])
        
        return jsonify({
            'success': True, 
            'message': f'{total_count}件の送信履歴をすべて削除しました',
            'deleted_count': total_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/view_file/<request_id>', methods=['GET'])
def view_file(request_id):
    """ファイルを表示"""
    try:
        params_list = load_parameters()
        if not isinstance(params_list, list):
            return jsonify({'success': False, 'error': 'パラメータデータが配列ではありません'}), 400
        
        # 指定されたIDのリクエストを探す
        for request in params_list:
            if request.get("id") == request_id:
                file_url = request.get("file_url")
                if not file_url:
                    return jsonify({'success': False, 'error': 'ファイルURLが見つかりません'}), 404
                
                # ローカルファイルの場合
                if file_url.startswith('file://'):
                    local_file_path = file_url[7:]
                    if local_file_path.startswith('/'):
                        local_file_path = local_file_path[1:]
                    
                    if os.path.exists(local_file_path):
                        # ファイルの拡張子に応じて適切なContent-Typeを設定
                        ext = os.path.splitext(local_file_path)[1].lower()
                        content_types = {
                            '.pdf': 'application/pdf',
                            '.png': 'image/png',
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.tiff': 'image/tiff',
                            '.tif': 'image/tiff'
                        }
                        content_type = content_types.get(ext, 'application/octet-stream')
                        
                        with open(local_file_path, 'rb') as f:
                            file_content = f.read()
                        
                        from flask import Response
                        return Response(file_content, mimetype=content_type)
                    else:
                        print(f"ファイルが見つかりません: {local_file_path}")
                        return jsonify({'success': False, 'error': f'ファイルが見つかりません: {os.path.basename(local_file_path)}'}), 404
                
                # URLファイルの場合
                else:
                    # URLをそのまま返す（リダイレクト）
                    from flask import redirect
                    return redirect(file_url)
        
        return jsonify({'success': False, 'error': '該当する送信が見つかりません'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/view_converted_pdf/<request_id>', methods=['GET'])
def view_converted_pdf(request_id):
    """変換されたPDFファイルを表示"""
    try:
        params_list = load_parameters()
        if not isinstance(params_list, list):
            return jsonify({'success': False, 'error': 'パラメータデータが配列ではありません'}), 400
        
        # 指定されたIDのリクエストを探す
        for request in params_list:
            if request.get("id") == request_id:
                converted_pdf_path = request.get("converted_pdf_path")
                if not converted_pdf_path:
                    return jsonify({'success': False, 'error': '変換されたPDFファイルの情報がありません'}), 404
                
                if os.path.exists(converted_pdf_path):
                    with open(converted_pdf_path, 'rb') as f:
                        file_content = f.read()
                    
                    from flask import Response
                    return Response(file_content, mimetype='application/pdf')
                else:
                    print(f"変換されたPDFファイルが見つかりません: {converted_pdf_path}")
                    # ファイルが存在しない場合、元ファイルから再生成を試行
                    return try_regenerate_converted_pdf(request_id, request)
        
        return jsonify({'success': False, 'error': '該当する送信が見つかりません'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/<request_id>', methods=['GET'])
def request_detail(request_id):
    """リクエスト詳細画面を表示"""
    try:
        params_list = load_parameters()
        if not isinstance(params_list, list):
            return "パラメータデータが配列ではありません", 400
        
        # 指定されたIDのリクエストを探す
        for request_data in params_list:
            if request_data.get("id") == request_id:
                # ステータステキストとクラスを取得
                status = request_data.get("status")
                status_map = {
                    0: ("待機中", "status-pending"),
                    1: ("完了", "status-completed"),
                    2: ("処理中", "status-processing"),
                    -1: ("エラー", "status-error")
                }
                status_text, status_class = status_map.get(status, ("不明", ""))
                
                # 日時をフォーマット
                from datetime import datetime
                created_at = datetime.fromisoformat(request_data.get("created_at")).strftime("%Y年%m月%d日 %H:%M:%S") if request_data.get("created_at") else "不明"
                updated_at = datetime.fromisoformat(request_data.get("updated_at")).strftime("%Y年%m月%d日 %H:%M:%S") if request_data.get("updated_at") else "不明"
                
                # 元ファイルの存在確認
                file_url = request_data.get("file_url")
                has_original_file = False
                if file_url:
                    if file_url.startswith('file://'):
                        local_file_path = file_url[7:]
                        if local_file_path.startswith('/'):
                            local_file_path = local_file_path[1:]
                        has_original_file = os.path.exists(local_file_path)
                    else:
                        has_original_file = True  # URLの場合は存在すると仮定
                
                return render_template('detail.html',
                    request_data=request_data,
                    status_text=status_text,
                    status_class=status_class,
                    created_at=created_at,
                    updated_at=updated_at,
                    has_original_file=has_original_file
                )
        
        return "該当するリクエストが見つかりません", 404
    except Exception as e:
        return f"エラーが発生しました: {str(e)}", 500

if __name__ == '__main__':
    worker_thread = threading.Thread(target=fax_worker, daemon=True)
    worker_thread.start()
    print("FAX送信APIサーバー起動中...")
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
