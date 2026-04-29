import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class PersistenceManager:
    def __init__(self, db_path: str = "chat_history.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    model_used TEXT,
                    api_source TEXT,
                    summary TEXT
                )
            ''')

            # Messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP,
                    tokens_used INTEGER,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            ''')

            # Metadata table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            conn.commit()

    def save_session(self, session_id: str, name: str, model_used: str = "", api_source: str = ""):
        """Save or update a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute('''
                INSERT OR REPLACE INTO sessions
                (session_id, name, created_at, updated_at, model_used, api_source)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session_id, name, now, now, model_used, api_source))

            conn.commit()

    def save_message(self, session_id: str, role: str, content: str, tokens_used: int = 0):
        """Save a message to the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO messages (session_id, role, content, timestamp, tokens_used)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, role, content, now, tokens_used))

            conn.commit()

    def load_sessions(self) -> Dict[str, Dict]:
        """Load all sessions from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sessions ORDER BY updated_at DESC')
            rows = cursor.fetchall()

            sessions = {}
            for row in rows:
                session_id, name, created_at, updated_at, model_used, api_source, summary = row
                sessions[session_id] = {
                    "name": name,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "model_used": model_used,
                    "api_source": api_source,
                    "summary": summary,
                    "messages": self.load_messages(session_id)
                }

            return sessions

    def load_messages(self, session_id: str) -> List[Dict]:
        """Load messages for a specific session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT role, content, timestamp, tokens_used
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            ''', (session_id,))

            rows = cursor.fetchall()
            messages = []
            for row in rows:
                role, content, timestamp, tokens_used = row
                messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": timestamp,
                    "tokens_used": tokens_used
                })

            return messages

    def delete_session(self, session_id: str):
        """Delete a session and its messages"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM messages WHERE session_id = ?', (session_id,))
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))

            conn.commit()

    def search_messages(self, query: str) -> List[Dict]:
        """Search messages across all sessions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.name, m.role, m.content, m.timestamp, s.session_id
                FROM messages m
                JOIN sessions s ON m.session_id = s.session_id
                WHERE m.content LIKE ?
                ORDER BY m.timestamp DESC
                LIMIT 50
            ''', (f'%{query}%',))

            rows = cursor.fetchall()
            results = []
            for row in rows:
                session_name, role, content, timestamp, session_id = row
                results.append({
                    "session_name": session_name,
                    "role": role,
                    "content": content,
                    "timestamp": timestamp,
                    "session_id": session_id
                })

            return results

    def export_session(self, session_id: str, format_type: str = "json") -> str:
        """Export a session to JSON or text format"""
        messages = self.load_messages(session_id)

        if format_type == "json":
            return json.dumps({
                "session_id": session_id,
                "messages": messages
            }, indent=2, ensure_ascii=False)

        elif format_type == "txt":
            output = f"Session: {session_id}\n\n"
            for msg in messages:
                output += f"{msg['role'].upper()}: {msg['content']}\n\n"
            return output

        return ""

    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total messages
            cursor.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,))
            total_messages = cursor.fetchone()[0]

            # Total tokens
            cursor.execute('SELECT SUM(tokens_used) FROM messages WHERE session_id = ?', (session_id,))
            total_tokens = cursor.fetchone()[0] or 0

            return {
                "total_messages": total_messages,
                "total_tokens": total_tokens
            }