import mysql.connector
from datetime import datetime
import uuid

# MySQLに接続
mydb = mysql.connector.connect(
  host="akioka.cloud",
  port="3306",
  user="akioka_administrator",
  password="Akiokapass0",
  database="akioka_db"
)

mycursor = mydb.cursor()

# -------------------------------
# FAXパラメータデータベース操作
# -------------------------------

def load_parameters():
    """fax_parametersテーブルから全データを読み込み"""
    print("[load_parameters] テーブルからデータを読み込み開始")
    try:
        mycursor.execute("""
            SELECT id, file_url, fax_number, status, created_at, updated_at,
                   error_message, converted_pdf_path, request_user, file_name,
                   callback_url, order_destination
            FROM fax_parameters
            ORDER BY created_at ASC
        """)
        rows = mycursor.fetchall()
        print(f"[load_parameters] {len(rows)} 件のレコードを取得")

        # カラム名を取得
        columns = [desc[0] for desc in mycursor.description]
        print(f"[load_parameters] カラム: {columns}")

        # 辞書のリストに変換
        params_list = []
        for row in rows:
            param_dict = {}
            for i, col in enumerate(columns):
                # DATETIMEをISO形式の文字列に変換
                if isinstance(row[i], datetime):
                    param_dict[col] = row[i].isoformat()
                else:
                    param_dict[col] = row[i]
            params_list.append(param_dict)

        print(f"[load_parameters] 辞書変換完了: {len(params_list)} 件")
        return params_list
    except Exception as e:
        print(f"[load_parameters] エラー: {e}")
        import traceback
        traceback.print_exc()
        return []

def save_parameters(data):
    """パラメータデータを保存（未実装：個別更新関数を使用）"""
    # この関数は後方互換性のため保持（実際の保存は個別関数で行う）
    pass

def add_fax_request(file_url, fax_number, request_user=None, file_name=None, callback_url=None, order_destination=None):
    """新しいFAX送信リクエストを追加"""
    print(f"[add_fax_request] 新規リクエスト追加開始: {fax_number}")
    try:
        request_id = str(uuid.uuid4())
        created_at = datetime.now()

        print(f"[add_fax_request] 生成されたID: {request_id}")
        print(f"[add_fax_request] file_url: {file_url}")
        print(f"[add_fax_request] fax_number: {fax_number}")
        print(f"[add_fax_request] request_user: {request_user}")
        print(f"[add_fax_request] file_name: {file_name}")

        sql = """
            INSERT INTO fax_parameters
            (id, file_url, fax_number, status, created_at, updated_at, request_user, file_name, callback_url, order_destination)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        val = (request_id, file_url, fax_number, 0, created_at, created_at, request_user, file_name, callback_url, order_destination)
        print(f"[add_fax_request] INSERT実行")
        print(f"[add_fax_request] VALUES: {val}")

        mycursor.execute(sql, val)
        mydb.commit()
        print(f"[add_fax_request] INSERT成功、rowcount: {mycursor.rowcount}")

        # 作成したレコードを辞書形式で返す
        new_request = {
            "id": request_id,
            "file_url": file_url,
            "fax_number": fax_number,
            "status": 0,
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
            "error_message": None,
            "converted_pdf_path": None,
            "request_user": request_user,
            "file_name": file_name,
            "callback_url": callback_url,
            "order_destination": order_destination
        }

        print(f"[add_fax_request] リクエスト作成完了: {request_id}")
        return new_request
    except Exception as e:
        print(f"[add_fax_request] FAXリクエスト追加エラー: {e}")
        import traceback
        traceback.print_exc()
        mydb.rollback()
        raise e

def update_request_status(request_id, status, error_message=None):
    """リクエストのステータスを更新"""
    try:
        updated_at = datetime.now()

        sql = "UPDATE fax_parameters SET status = %s, updated_at = %s"
        val = [status, updated_at]

        if error_message is not None:
            sql += ", error_message = %s"
            val.append(error_message)

        sql += " WHERE id = %s"
        val.append(request_id)

        mycursor.execute(sql, val)
        mydb.commit()

        if mycursor.rowcount == 0:
            print(f"警告: ID {request_id} のレコードが見つかりません")
    except Exception as e:
        print(f"ステータス更新エラー: {e}")
        mydb.rollback()
        raise e

def update_request_converted_pdf(request_id, pdf_path):
    """リクエストの変換後PDFファイルパスを更新"""
    try:
        updated_at = datetime.now()

        sql = "UPDATE fax_parameters SET converted_pdf_path = %s, updated_at = %s WHERE id = %s"
        val = (pdf_path, updated_at, request_id)

        mycursor.execute(sql, val)
        mydb.commit()

        if mycursor.rowcount == 0:
            print(f"警告: ID {request_id} のレコードが見つかりません")
    except Exception as e:
        print(f"PDFパス更新エラー: {e}")
        mydb.rollback()
        raise e

def get_request_by_id(request_id):
    """指定されたIDのリクエストを取得"""
    try:
        sql = """
            SELECT id, file_url, fax_number, status, created_at, updated_at,
                   error_message, converted_pdf_path, request_user, file_name,
                   callback_url, order_destination
            FROM fax_parameters WHERE id = %s
        """
        mycursor.execute(sql, (request_id,))
        row = mycursor.fetchone()

        if row:
            columns = [desc[0] for desc in mycursor.description]
            param_dict = {}
            for i, col in enumerate(columns):
                if isinstance(row[i], datetime):
                    param_dict[col] = row[i].isoformat()
                else:
                    param_dict[col] = row[i]
            return param_dict
        return None
    except Exception as e:
        print(f"リクエスト取得エラー: {e}")
        return None

def clear_completed_requests():
    """完了済みの送信履歴を削除"""
    try:
        sql = "DELETE FROM fax_parameters WHERE status = 1"
        mycursor.execute(sql)
        deleted_count = mycursor.rowcount
        mydb.commit()
        return deleted_count
    except Exception as e:
        print(f"完了済み削除エラー: {e}")
        mydb.rollback()
        raise e

def retry_error_requests():
    """エラー状態の送信を再送状態に変更"""
    try:
        sql = "UPDATE fax_parameters SET status = 0, updated_at = %s, error_message = NULL WHERE status = -1"
        val = (datetime.now(),)
        mycursor.execute(sql, val)
        retry_count = mycursor.rowcount
        mydb.commit()
        return retry_count
    except Exception as e:
        print(f"エラーリトライエラー: {e}")
        mydb.rollback()
        raise e

def retry_request_by_id(request_id):
    """個別の送信を再送状態に変更"""
    try:
        # まず現在のステータスを確認
        sql_check = "SELECT status FROM fax_parameters WHERE id = %s"
        mycursor.execute(sql_check, (request_id,))
        result = mycursor.fetchone()

        if not result or result[0] != -1:
            return False, "エラー状態の送信のみ再送可能です"

        # 再送状態に変更
        sql_update = "UPDATE fax_parameters SET status = 0, updated_at = %s, error_message = NULL WHERE id = %s"
        val = (datetime.now(), request_id)
        mycursor.execute(sql_update, val)
        mydb.commit()

        if mycursor.rowcount > 0:
            return True, "送信を再送しました"
        else:
            return False, "該当する送信が見つかりません"
    except Exception as e:
        print(f"個別リトライエラー: {e}")
        mydb.rollback()
        return False, str(e)

def clear_all_requests():
    """すべての送信履歴を削除"""
    try:
        sql = "DELETE FROM fax_parameters"
        mycursor.execute(sql)
        deleted_count = mycursor.rowcount
        mydb.commit()
        return deleted_count
    except Exception as e:
        print(f"全削除エラー: {e}")
        mydb.rollback()
        raise e

# テスト用（stocksテーブルは削除予定）
if __name__ == "__main__":
    # データを取得するクエリ
    mycursor.execute("SELECT * FROM stocks where del_flg = 0")

    myresult = mycursor.fetchall()

    for x in myresult:
        print(x)