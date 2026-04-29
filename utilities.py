import json
import os
from typing import Dict, List, Any
from datetime import datetime, timedelta

class SessionAnalytics:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a session"""
        stats = self.db.get_session_stats(session_id)
        messages = self.db.load_messages(session_id)

        if not messages:
            return stats

        # Calculate additional metrics
        user_messages = [m for m in messages if m['role'] == 'user']
        assistant_messages = [m for m in messages if m['role'] == 'assistant']

        # Average message length
        avg_user_length = sum(len(m['content']) for m in user_messages) / len(user_messages) if user_messages else 0
        avg_assistant_length = sum(len(m['content']) for m in assistant_messages) / len(assistant_messages) if assistant_messages else 0

        # Time span
        timestamps = [datetime.fromisoformat(m['timestamp']) for m in messages]
        time_span = max(timestamps) - min(timestamps) if timestamps else timedelta(0)

        stats.update({
            "user_messages": len(user_messages),
            "assistant_messages": len(assistant_messages),
            "avg_user_message_length": round(avg_user_length, 1),
            "avg_assistant_message_length": round(avg_assistant_length, 1),
            "session_duration": str(time_span),
            "messages_per_hour": len(messages) / max(time_span.total_seconds() / 3600, 1)
        })

        return stats

    def get_user_stats(self) -> Dict[str, Any]:
        """Get overall user statistics"""
        sessions = self.db.load_sessions()

        total_sessions = len(sessions)
        total_messages = sum(len(s['messages']) for s in sessions.values())
        total_tokens = sum(sum(m.get('tokens_used', 0) for m in s['messages']) for s in sessions.values())

        # Most used model
        model_counts = {}
        for session in sessions.values():
            model = session.get('model_used', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1

        most_used_model = max(model_counts.items(), key=lambda x: x[1]) if model_counts else ('none', 0)

        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "total_tokens": total_tokens,
            "most_used_model": most_used_model[0],
            "avg_messages_per_session": total_messages / max(total_sessions, 1)
        }

class SessionManager:
    def __init__(self, db_manager):
        self.db = db_manager

    def export_session(self, session_id: str, format_type: str = "json") -> str:
        """Export session in specified format"""
        return self.db.export_session(session_id, format_type)

    def import_session(self, data: str, format_type: str = "json") -> str:
        """Import session from data string"""
        try:
            if format_type == "json":
                session_data = json.loads(data)
                session_id = session_data.get('session_id')
                messages = session_data.get('messages', [])

                # Save to database
                for msg in messages:
                    self.db.save_message(
                        session_id,
                        msg['role'],
                        msg['content'],
                        msg.get('tokens_used', 0)
                    )

                return f"Session {session_id} imported successfully"
            else:
                return "Unsupported import format"
        except Exception as e:
            return f"Import failed: {str(e)}"

    def backup_all_sessions(self, backup_path: str = "chat_backup.json") -> str:
        """Create a backup of all sessions"""
        try:
            sessions = self.db.load_sessions()
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, indent=2, ensure_ascii=False)
            return f"Backup created: {backup_path}"
        except Exception as e:
            return f"Backup failed: {str(e)}"

    def restore_from_backup(self, backup_path: str) -> str:
        """Restore sessions from backup"""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                sessions = json.load(f)

            restored_count = 0
            for session_id, session_data in sessions.items():
                self.db.save_session(
                    session_id,
                    session_data['name'],
                    session_data.get('model_used', ''),
                    session_data.get('api_source', '')
                )

                for msg in session_data['messages']:
                    self.db.save_message(
                        session_id,
                        msg['role'],
                        msg['content'],
                        msg.get('tokens_used', 0)
                    )
                restored_count += 1

            return f"Restored {restored_count} sessions"
        except Exception as e:
            return f"Restore failed: {str(e)}"

class CodeExecutor:
    def __init__(self):
        self.allowed_modules = ['math', 'random', 'datetime', 'json', 're']

    def execute_python(self, code: str, timeout: int = 10) -> str:
        """Execute Python code with restrictions"""
        # This is a simplified version - in production, use RestrictedPython
        try:
            # Basic security check
            if any(module in code for module in ['os', 'sys', 'subprocess', 'importlib']):
                return "Error: Unsafe code detected"

            # Execute in isolated environment
            local_vars = {}
            exec(code, {'__builtins__': {}}, local_vars)

            # Get output (if any print statements were used, this won't capture them)
            return f"Code executed successfully. Local variables: {list(local_vars.keys())}"
        except Exception as e:
            return f"Execution error: {str(e)}"

def create_requirements_file():
    """Create requirements.txt with all necessary dependencies"""
    requirements = [
        "streamlit",
        "openai",
        "python-dotenv",
        "Pillow",
        "duckduckgo-search",
        "RestrictedPython"
    ]

    with open("requirements.txt", "w") as f:
        f.write("\n".join(requirements))

    return "requirements.txt created"