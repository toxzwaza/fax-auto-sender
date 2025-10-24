from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import os
import json
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from db import (load_parameters, add_fax_request, update_request_status,
                update_request_converted_pdf, get_request_by_id, clear_completed_requests,
                retry_error_requests, retry_request_by_id, clear_all_requests)

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

# FAX送信処理は別ファイル（fax_worker.py）で実行

# -------------------------------
# データベース操作（db.pyからインポート済み）
# -------------------------------

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
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from PIL import Image
    
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

# コールバック通知機能はfax_worker.pyに移動

# FAX送信処理はfax_worker.pyに移動

# -------------------------------
# Flask API
# -------------------------------

@app.route('/send_fax', methods=['POST'])
def send_fax_api():
    """FAX送信API（URL指定）"""
    try:
        data = request.get_json()
        print("=" * 50)
        print("[API] /send_fax - FAX送信リクエスト受信")
        print(f"[API] 受信データ: {data}")
        print("-" * 30)

        file_url = data.get('file_url')
        fax_number = data.get('fax_number')
        request_user = data.get('request_user')  # オプション
        file_name = data.get('file_name')  # オプション
        callback_url = data.get('callback_url')  # オプション
        order_destination = data.get('order_destination')  # オプション

        print(f"[API] file_url: {file_url}")
        print(f"[API] fax_number: {fax_number}")
        print(f"[API] request_user: {request_user}")
        print(f"[API] file_name: {file_name}")
        print(f"[API] callback_url: {callback_url}")
        print(f"[API] order_destination: {order_destination}")

        if not file_url or not fax_number:
            print("[API] エラー: file_urlとfax_numberは必須です")
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
        print("=" * 50)
        print("[API] /upload_and_send_fax - ファイルアップロード＆FAX送信リクエスト受信")
        print(f"[API] 受信ファイル: {request.files}")
        print(f"[API] 受信フォーム: {request.form}")
        print("-" * 30)

        # ファイルの確認
        if 'file' not in request.files:
            print("[API] エラー: ファイルが選択されていません")
            return jsonify({'success': False, 'error': 'ファイルが選択されていません'}), 400

        file = request.files['file']
        fax_number = request.form.get('fax_number')
        request_user = request.form.get('request_user')  # オプション
        file_name = request.form.get('file_name')  # オプション
        callback_url = request.form.get('callback_url')  # オプション
        order_destination = request.form.get('order_destination')  # オプション

        print(f"[API] ファイル名: {file.filename if file else 'None'}")
        print(f"[API] fax_number: {fax_number}")
        print(f"[API] request_user: {request_user}")
        print(f"[API] file_name: {file_name}")
        print(f"[API] callback_url: {callback_url}")
        print(f"[API] order_destination: {order_destination}")

        if not fax_number:
            print("[API] エラー: fax_numberは必須です")
            return jsonify({'success': False, 'error': 'fax_numberは必須です'}), 400

        if file.filename == '':
            print("[API] エラー: ファイルが選択されていません")
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
    print("=" * 50)
    print(f"[API] /status/{request_id} - ステータス確認リクエスト")
    print(f"[API] request_id: {request_id}")

    request_data = get_request_by_id(request_id)
    if request_data:
        print(f"[API] ステータス取得成功: {request_data.get('status', '不明')}")
        return jsonify({'success': True, 'request': request_data})
    print("[API] エラー: 該当リクエストなし")
    return jsonify({'success': False, 'error': '該当リクエストなし'}), 404

@app.route('/requests', methods=['GET'])
def get_all_requests():
    """全リクエスト一覧"""
    print("=" * 50)
    print("[API] /requests - 全リクエスト一覧取得")

    params_list = load_parameters()
    print(f"[API] 取得件数: {len(params_list)}")

    return jsonify({'success': True, 'requests': params_list, 'total': len(params_list)})

@app.route('/health', methods=['GET'])
def health():
    print("=" * 50)
    print("[API] /health - ヘルスチェック")

    response = jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})
    print("[API] ヘルスチェック成功")
    return response

@app.route('/', methods=['GET'])
def admin():
    """管理画面を表示"""
    print("=" * 50)
    print("[API] / - 管理画面表示")

    print("[API] admin.htmlテンプレート表示")
    return render_template('admin.html')

@app.route('/clear_completed', methods=['POST'])
def clear_completed():
    """完了済みの送信履歴を削除"""
    print("=" * 50)
    print("[API] /clear_completed - 完了済み送信履歴削除")

    try:
        deleted_count = clear_completed_requests()
        print(f"[API] 削除件数: {deleted_count}")

        return jsonify({
            'success': True,
            'message': f'{deleted_count}件の完了済み送信履歴を削除しました',
            'deleted_count': deleted_count
        })
    except Exception as e:
        print(f"[API] エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/retry_errors', methods=['POST'])
def retry_errors():
    """エラー状態の送信を再送"""
    print("=" * 50)
    print("[API] /retry_errors - エラー送信再送")

    try:
        retry_count = retry_error_requests()
        print(f"[API] 再送件数: {retry_count}")

        return jsonify({
            'success': True,
            'message': f'{retry_count}件のエラー送信を再送しました',
            'retry_count': retry_count
        })
    except Exception as e:
        print(f"[API] エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/retry_request/<request_id>', methods=['POST'])
def retry_request(request_id):
    """個別の送信を再送"""
    print("=" * 50)
    print(f"[API] /retry_request/{request_id} - 個別送信再送")
    print(f"[API] request_id: {request_id}")

    try:
        success, message = retry_request_by_id(request_id)
        print(f"[API] 結果: {'成功' if success else '失敗'} - {message}")

        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 400
    except Exception as e:
        print(f"[API] エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/clear_all', methods=['POST'])
def clear_all():
    """すべての送信履歴を削除"""
    print("=" * 50)
    print("[API] /clear_all - 全送信履歴削除")

    try:
        deleted_count = clear_all_requests()
        print(f"[API] 削除件数: {deleted_count}")

        return jsonify({
            'success': True,
            'message': f'{deleted_count}件の送信履歴をすべて削除しました',
            'deleted_count': deleted_count
        })
    except Exception as e:
        print(f"[API] エラー: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/view_file/<request_id>', methods=['GET'])
def view_file(request_id):
    """ファイルを表示"""
    print("=" * 50)
    print(f"[API] /view_file/{request_id} - ファイル表示")
    print(f"[API] request_id: {request_id}")

    try:
        request_data = get_request_by_id(request_id)
        if request_data:
            file_url = request_data.get("file_url")
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
    print("=" * 50)
    print(f"[API] /view_converted_pdf/{request_id} - PDF表示")
    print(f"[API] request_id: {request_id}")

    try:
        request_data = get_request_by_id(request_id)
        if request_data:
            converted_pdf_path = request_data.get("converted_pdf_path")
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
                return try_regenerate_converted_pdf(request_id, request_data)

        return jsonify({'success': False, 'error': '該当する送信が見つかりません'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/<request_id>', methods=['GET'])
def request_detail(request_id):
    """リクエスト詳細画面を表示"""
    print("=" * 50)
    print(f"[API] /{request_id} - リクエスト詳細画面")
    print(f"[API] request_id: {request_id}")

    try:
        request_data = get_request_by_id(request_id)
        if request_data:
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
    print("FAX送信APIサーバー起動中...")
    print("FAX送信処理は別途 fax_worker.py を実行してください")
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
