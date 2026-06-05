"""
WhatsApp Export Dashboard - Backend Server
==========================================
Existing project folder mein yeh file daalo aur chalao:
    python dashboard_server.py

Browser mein khulega: http://localhost:5000
"""

import os
import sys
import json
import sqlite3
import threading
import webbrowser
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# ── Existing project ka path auto-detect ──────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from config import DATA_DIR, DB_PATH
    from drive_uploader import DriveUploader
    DRIVE_AVAILABLE = True
except ImportError:
    print("[Server] ⚠️  config.py ya drive_uploader.py nahi mila — demo mode mein chalega")
    DRIVE_AVAILABLE = False
    DATA_DIR = os.path.join(BASE_DIR, "data")
    DB_PATH = os.path.join(DATA_DIR, "progress.db")

# ── Drive + DB se data fetch karna ────────────────────────────────────────────

def get_db_status_map():
    """SQLite se har chat ka status aur error fetch karo"""
    status_map = {}
    if not os.path.exists(DB_PATH):
        return status_map
    try:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT chat_name, chat_type, status, error_message, attempt_count, exported_at FROM chats"
        ).fetchall()
        conn.close()
        for row in rows:
            name, chat_type, status, error, attempts, exported_at = row
            status_map[name] = {
                "type": chat_type,
                "status": status,
                "error": error,
                "attempts": attempts,
                "exported_at": exported_at,
            }
    except Exception as e:
        print(f"[DB] Error: {e}")
    return status_map


def bytes_to_human(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


def fetch_drive_data():
    """
    Google Drive se WhatsApp Exports folder ka data fetch karo.
    Structure: WhatsApp Exports / Personal Chats|Group Chats / [Chat Name] / files
    """
    if not DRIVE_AVAILABLE:
        return _demo_data()

    try:
        drive = DriveUploader()
        service = drive.service

        # Root folder dhundho
        root_query = (
            "name='WhatsApp Exports' and "
            "mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        root_res = service.files().list(q=root_query, fields="files(id,name)").execute()
        roots = root_res.get('files', [])

        if not roots:
            print("[Drive] 'WhatsApp Exports' folder nahi mila Drive pe")
            return _db_only_data()

        root_id = roots[0]['id']
        print(f"[Drive] Root folder mila: {root_id}")

        # Personal aur Group subfolders
        sub_query = (
            f"'{root_id}' in parents and "
            "mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        sub_res = service.files().list(q=sub_query, fields="files(id,name)").execute()
        subfolders = {f['name']: f['id'] for f in sub_res.get('files', [])}

        db_map = get_db_status_map()
        groups = []
        personal = []

        for folder_name, folder_id in subfolders.items():
            is_group = "group" in folder_name.lower()
            target_list = groups if is_group else personal

            # Har chat folder dhundho
            chat_query = (
                f"'{folder_id}' in parents and "
                "mimeType='application/vnd.google-apps.folder' and trashed=false"
            )
            page_token = None
            while True:
                params = dict(
                    q=chat_query,
                    fields="nextPageToken,files(id,name)",
                    pageSize=200,
                )
                if page_token:
                    params['pageToken'] = page_token
                chat_res = service.files().list(**params).execute()
                chat_folders = chat_res.get('files', [])

                for chat_folder in chat_folders:
                    chat_name = chat_folder['name']
                    chat_folder_id = chat_folder['id']

                    # Files list karo is chat mein
                    files_query = f"'{chat_folder_id}' in parents and trashed=false"
                    files_res = service.files().list(
                        q=files_query,
                        fields="files(id,name,size,createdTime,mimeType)",
                        pageSize=50,
                    ).execute()
                    files = files_res.get('files', [])

                    total_size = sum(int(f.get('size', 0)) for f in files)
                    file_count = len(files)

                    # Latest file ka date
                    latest_date = None
                    if files:
                        dates = [f.get('createdTime', '') for f in files if f.get('createdTime')]
                        if dates:
                            latest_date = max(dates)[:10]  # YYYY-MM-DD

                    # DB se status merge karo
                    db_info = db_map.get(chat_name, {})
                    status = db_info.get('status', 'exported' if file_count > 0 else 'unknown')

                    chat_entry = {
                        "name": chat_name,
                        "type": "group" if is_group else "personal",
                        "file_count": file_count,
                        "size_bytes": total_size,
                        "size_human": bytes_to_human(total_size),
                        "latest_date": latest_date,
                        "status": status,
                        "error": db_info.get('error'),
                        "attempts": db_info.get('attempts', 0),
                        "exported_at": db_info.get('exported_at'),
                        "drive_folder_id": chat_folder_id,
                    }
                    target_list.append(chat_entry)

                page_token = chat_res.get('nextPageToken')
                if not page_token:
                    break

        # Summary stats
        all_chats = groups + personal
        total_size = sum(c['size_bytes'] for c in all_chats)
        exported_count = sum(1 for c in all_chats if c['status'] == 'exported')
        failed_count = sum(1 for c in all_chats if c['status'] == 'failed')

        return {
            "groups": sorted(groups, key=lambda x: x['name'].lower()),
            "personal": sorted(personal, key=lambda x: x['name'].lower()),
            "stats": {
                "total": len(all_chats),
                "groups_count": len(groups),
                "personal_count": len(personal),
                "exported": exported_count,
                "failed": failed_count,
                "pending": len(all_chats) - exported_count - failed_count,
                "total_size": bytes_to_human(total_size),
                "total_size_bytes": total_size,
            },
            "fetched_at": datetime.now().isoformat(),
            "source": "drive",
        }

    except Exception as e:
        print(f"[Drive] Error: {e}")
        return _db_only_data()


def _db_only_data():
    """Sirf SQLite DB se data — Drive connect nahi hua"""
    db_map = get_db_status_map()
    groups = []
    personal = []

    for name, info in db_map.items():
        entry = {
            "name": name,
            "type": info['type'],
            "file_count": 0,
            "size_bytes": 0,
            "size_human": "—",
            "latest_date": info.get('exported_at', '—'),
            "status": info['status'],
            "error": info.get('error'),
            "attempts": info.get('attempts', 0),
            "exported_at": info.get('exported_at'),
            "drive_folder_id": None,
        }
        if info['type'] == 'group':
            groups.append(entry)
        else:
            personal.append(entry)

    all_chats = groups + personal
    exported = sum(1 for c in all_chats if c['status'] == 'exported')
    failed = sum(1 for c in all_chats if c['status'] == 'failed')

    return {
        "groups": sorted(groups, key=lambda x: x['name'].lower()),
        "personal": sorted(personal, key=lambda x: x['name'].lower()),
        "stats": {
            "total": len(all_chats),
            "groups_count": len(groups),
            "personal_count": len(personal),
            "exported": exported,
            "failed": failed,
            "pending": len(all_chats) - exported - failed,
            "total_size": "—",
            "total_size_bytes": 0,
        },
        "fetched_at": datetime.now().isoformat(),
        "source": "db_only",
    }


def _demo_data():
    """Demo data — jab config.py nahi hota"""
    import random
    groups = [
        {"name": "Family mehfil", "type": "group", "file_count": 47, "size_bytes": 13000000, "size_human": "12.4 MB", "latest_date": "2026-06-05", "status": "exported", "error": None, "attempts": 1, "exported_at": "2026-06-05", "drive_folder_id": "demo"},
        {"name": "Office team 2025", "type": "group", "file_count": 23, "size_bytes": 8500000, "size_human": "8.1 MB", "latest_date": "2026-06-04", "status": "exported", "error": None, "attempts": 1, "exported_at": "2026-06-04", "drive_folder_id": "demo"},
        {"name": "School classmates", "type": "group", "file_count": 89, "size_bytes": 35900000, "size_human": "34.2 MB", "latest_date": "2026-06-03", "status": "exported", "error": None, "attempts": 1, "exported_at": "2026-06-03", "drive_folder_id": "demo"},
        {"name": "Batch 2019 alumni", "type": "group", "file_count": 0, "size_bytes": 0, "size_human": "—", "latest_date": None, "status": "failed", "error": "Drive pe file nahi mili", "attempts": 3, "exported_at": None, "drive_folder_id": None},
        {"name": "Neighbors colony", "type": "group", "file_count": 8, "size_bytes": 1200000, "size_human": "1.1 MB", "latest_date": "2026-06-01", "status": "exported", "error": None, "attempts": 1, "exported_at": "2026-06-01", "drive_folder_id": "demo"},
    ]
    personal = [
        {"name": "Amit Mishra", "type": "personal", "file_count": 3, "size_bytes": 850000, "size_human": "0.8 MB", "latest_date": "2026-06-05", "status": "exported", "error": None, "attempts": 1, "exported_at": "2026-06-05", "drive_folder_id": "demo"},
        {"name": "Priya Kapoor", "type": "personal", "file_count": 12, "size_bytes": 4300000, "size_human": "4.1 MB", "latest_date": "2026-06-05", "status": "exported", "error": None, "attempts": 1, "exported_at": "2026-06-05", "drive_folder_id": "demo"},
        {"name": "Rahul Sharma", "type": "personal", "file_count": 1, "size_bytes": 100000, "size_human": "0.1 MB", "latest_date": "2026-06-04", "status": "exported", "error": None, "attempts": 1, "exported_at": "2026-06-04", "drive_folder_id": "demo"},
        {"name": "Vikram Joshi", "type": "personal", "file_count": 0, "size_bytes": 0, "size_human": "—", "latest_date": None, "status": "pending", "error": None, "attempts": 0, "exported_at": None, "drive_folder_id": None},
        {"name": "Arjun Kumar", "type": "personal", "file_count": 0, "size_bytes": 0, "size_human": "—", "latest_date": None, "status": "failed", "error": "Chat open nahi hua", "attempts": 3, "exported_at": None, "drive_folder_id": None},
    ]
    all_chats = groups + personal
    exported = sum(1 for c in all_chats if c['status'] == 'exported')
    failed = sum(1 for c in all_chats if c['status'] == 'failed')
    total_bytes = sum(c['size_bytes'] for c in all_chats)
    return {
        "groups": groups,
        "personal": personal,
        "stats": {
            "total": len(all_chats),
            "groups_count": len(groups),
            "personal_count": len(personal),
            "exported": exported,
            "failed": failed,
            "pending": len(all_chats) - exported - failed,
            "total_size": bytes_to_human(total_bytes),
            "total_size_bytes": total_bytes,
        },
        "fetched_at": datetime.now().isoformat(),
        "source": "demo",
    }


# ── HTTP Server ────────────────────────────────────────────────────────────────

DASHBOARD_HTML_PATH = os.path.join(BASE_DIR, "dashboard.html")
_cached_data = None
_cache_time = None
CACHE_SECONDS = 60  # 1 minute cache


class DashboardHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # quiet server logs

    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard.html":
            self._serve_file(DASHBOARD_HTML_PATH, "text/html")
        elif self.path == "/api/data":
            self._serve_api()
        elif self.path == "/api/refresh":
            global _cached_data, _cache_time
            _cached_data = None
            _cache_time = None
            self._serve_api()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_file(self, path, content_type):
        try:
            with open(path, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"dashboard.html nahi mila")

    def _serve_api(self):
        global _cached_data, _cache_time
        import time

        now = time.time()
        if _cached_data is None or _cache_time is None or (now - _cache_time) > CACHE_SECONDS:
            print("[Server] Drive se fresh data fetch kar raha hai...")
            _cached_data = fetch_drive_data()
            _cache_time = now
            print(f"[Server] Data ready — {_cached_data['stats']['total']} chats")

        body = json.dumps(_cached_data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    PORT = 5000
    server = HTTPServer(("localhost", PORT), DashboardHandler)

    url = f"http://localhost:{PORT}"
    print(f"\n{'='*50}")
    print(f"  WhatsApp Export Dashboard")
    print(f"{'='*50}")
    print(f"  URL    : {url}")
    print(f"  Drive  : {'Connected' if DRIVE_AVAILABLE else 'Demo mode'}")
    print(f"  DB     : {DB_PATH}")
    print(f"{'='*50}")
    print(f"\n  Ctrl+C se band karo\n")

    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Band ho raha hai...")
        server.shutdown()
