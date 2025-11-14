import mysql.connector
from datetime import datetime
import uuid
import requests

DB_CONFIG = {
    "host": "akioka.cloud",
    "port": 3306,
    "user": "akioka_administrator",
    "password": "Akiokapass0",
    "database": "akioka_db"
}

def get_connection():
    """毎回新しい DB コネクションを取得"""
    return mysql.connector.connect(**DB_CONFIG)


# -------------------------------
# FAXパラメータデータベース操作
# -------------------------------

def load_parameters():
    print("[load_parameters] 取得開始")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, file_url, fax_number, status, created_at, updated_at,
                           error_message, converted_pdf_path, request_user, file_name,
                           callback_url, order_destination
                    FROM fax_parameters
                    ORDER BY created_at ASC
                """)
                rows = cur.fetchall()

                columns = [d[0] for d in cur.description]

                return [
                    {
                        col: (val.isoformat() if isinstance(val, datetime) else val)
                        for col, val in zip(columns, row)
                    }
                    for row in rows
                ]
    except Exception as e:
        print(f"[load_parameters] エラー: {e}")
        return []


def add_fax_request(file_url, fax_number, request_user=None, file_name=None, callback_url=None, order_destination=None):
    print(f"[add_fax_request] 開始: {fax_number}")
    try:
        request_id = str(uuid.uuid4())
        now = datetime.now()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO fax_parameters
                    (id, file_url, fax_number, status, created_at, updated_at, request_user, file_name, callback_url, order_destination)
                    VALUES (%s, %s, %s, 0, %s, %s, %s, %s, %s, %s)
                """, (request_id, file_url, fax_number, now, now, request_user, file_name, callback_url, order_destination))
                conn.commit()

        return {
            "id": request_id,
            "file_url": file_url,
            "fax_number": fax_number,
            "status": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "error_message": None,
            "converted_pdf_path": None,
            "request_user": request_user,
            "file_name": file_name,
            "callback_url": callback_url,
            "order_destination": order_destination
        }
    except Exception as e:
        print(f"[add_fax_request] エラー: {e}")
        raise e


def update_request_status(request_id, status, error_message=None):
    try:
        now = datetime.now()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE fax_parameters SET status=%s, updated_at=%s, error_message=%s WHERE id=%s",
                    (status, now, error_message, request_id)
                )
                conn.commit()
    except Exception as e:
        print(f"[update_request_status] エラー: {e}")
        raise e


def update_request_converted_pdf(request_id, pdf_path):
    try:
        now = datetime.now()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE fax_parameters SET converted_pdf_path=%s, updated_at=%s WHERE id=%s",
                    (pdf_path, now, request_id)
                )
                conn.commit()
    except Exception as e:
        print(f"[update_request_converted_pdf] エラー: {e}")
        raise e


def get_request_by_id(request_id):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, file_url, fax_number, status, created_at, updated_at,
                           error_message, converted_pdf_path, request_user, file_name,
                           callback_url, order_destination
                    FROM fax_parameters WHERE id=%s
                """, (request_id,))
                row = cur.fetchone()

        if not row:
            return None

        columns = ["id", "file_url", "fax_number", "status", "created_at", "updated_at",
                   "error_message", "converted_pdf_path", "request_user", "file_name",
                   "callback_url", "order_destination"]

        return {
            col: (val.isoformat() if isinstance(val, datetime) else val)
            for col, val in zip(columns, row)
        }

    except Exception as e:
        print(f"[get_request_by_id] エラー: {e}")
        return None


def clear_completed_requests():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM fax_parameters WHERE status = 1")
                deleted = cur.rowcount
                conn.commit()
                return deleted
    except Exception as e:
        print(f"[clear_completed_requests] エラー: {e}")
        raise e


def retry_error_requests():
    try:
        now = datetime.now()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE fax_parameters SET status = 0, updated_at = %s, error_message = NULL WHERE status = -1", (now,))
                count = cur.rowcount
                conn.commit()
                return count
    except Exception as e:
        print(f"[retry_error_requests] エラー: {e}")
        raise e


def retry_request_by_id(request_id):
    try:
        now = datetime.now()
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE fax_parameters SET status = 0, updated_at = %s, error_message = NULL WHERE id=%s AND status = -1", (now, request_id))
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        print(f"[retry_request_by_id] エラー: {e}")
        return False


def send_callback_notification(request_data):
    try:
        url = request_data.get("callback_url")
        if not url:
            return

        payload = {
            **request_data,
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }

        requests.post(url, json=payload, timeout=30)

    except Exception as e:
        print(f"[send_callback_notification] エラー: {e}")

def clear_all_requests():
    """fax_parameters テーブルの全データを削除"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM fax_parameters")
                deleted = cur.rowcount
                conn.commit()
                return deleted
    except Exception as e:
        print(f"[clear_all_requests] エラー: {e}")
        raise e


def get_initial_order_id(initial_order_id):
    """initial_ordersテーブルから指定IDのデータを取得"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM initial_orders WHERE id = %s", (initial_order_id,))
                row = cur.fetchone()
                return row[0] if row else None
    except Exception as e:
        print(f"[get_initial_order_id] エラー: {e}")
        return None


def update_initial_order_fax_parameter_id(initial_order_id, fax_request_id):
    """initial_ordersテーブルのfax_parameter_idを更新"""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE initial_orders SET fax_parameter_id=%s WHERE id=%s",
                    (fax_request_id, initial_order_id)
                )
                conn.commit()
                return cur.rowcount > 0
    except Exception as e:
        print(f"[update_initial_order_fax_parameter_id] エラー: {e}")
        return False