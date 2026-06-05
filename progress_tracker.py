import sqlite3
import json
from datetime import datetime
from config import DB_PATH
import os

class ProgressTracker:
    """
    SQLite based progress tracker.
    Process interrupt hone par resume kar sakta hai.
    """
    
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self._create_tables()
    
    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_name TEXT UNIQUE NOT NULL,
                chat_type TEXT DEFAULT 'personal',  -- personal / group
                status TEXT DEFAULT 'pending',       -- pending/exported/failed/skipped
                export_path TEXT,
                attempt_count INTEGER DEFAULT 0,
                error_message TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                exported_at TIMESTAMP
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS session_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def add_chat(self, chat_name: str, chat_type: str = "personal"):
        """Naya chat add karein (agar already exist karta hai toh skip)"""
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO chats (chat_name, chat_type) VALUES (?, ?)",
                (chat_name, chat_type)
            )
            self.conn.commit()
        except Exception as e:
            print(f"[DB] Chat add error: {e}")
    
    def mark_exported(self, chat_name: str, export_path: str):
        self.conn.execute("""
            UPDATE chats 
            SET status='exported', export_path=?, exported_at=CURRENT_TIMESTAMP
            WHERE chat_name=?
        """, (export_path, chat_name))
        self.conn.commit()
    
    def mark_failed(self, chat_name: str, error: str):
        self.conn.execute("""
            UPDATE chats 
            SET status='failed', error_message=?, attempt_count=attempt_count+1
            WHERE chat_name=?
        """, (error, chat_name))
        self.conn.commit()
    
    def mark_in_progress(self, chat_name: str):
        self.conn.execute(
            "UPDATE chats SET status='in_progress', attempt_count=attempt_count+1 WHERE chat_name=?",
            (chat_name,)
        )
        self.conn.commit()
    
    def is_exported(self, chat_name: str) -> bool:
        cursor = self.conn.execute(
            "SELECT status FROM chats WHERE chat_name=?", (chat_name,)
        )
        row = cursor.fetchone()
        return row and row[0] == 'exported'
    
    def get_pending_chats(self):
        cursor = self.conn.execute(
            "SELECT chat_name, chat_type FROM chats WHERE status IN ('pending', 'failed') AND attempt_count < 3"
        )
        return cursor.fetchall()
    
    def get_stats(self) -> dict:
        stats = {}
        for status in ['pending', 'exported', 'failed', 'in_progress']:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM chats WHERE status=?", (status,)
            )
            stats[status] = cursor.fetchone()[0]
        stats['total'] = sum(stats.values())
        return stats
    
    def log_event(self, event: str, details: str = ""):
        self.conn.execute(
            "INSERT INTO session_log (event, details) VALUES (?, ?)",
            (event, details)
        )
        self.conn.commit()
    
    def get_all_chats(self):
        cursor = self.conn.execute("SELECT chat_name, chat_type, status, export_path FROM chats")
        return cursor.fetchall()