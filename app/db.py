"""Database operations for the AI Assistant application."""

import sqlite3
from datetime import datetime
from pathlib import Path

from loguru import logger

from .models import Chat, Message, Preset, PresetField, PresetRun, Settings

DB_PATH = Path("ai_assistant.db")


class Database:
    """SQLite database manager."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        """Initialize database connection."""
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None
        self._connect()
        self._create_schema()

    def _connect(self) -> None:
        """Connect to the database."""
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            logger.info(f"Connected to database at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()

            # Settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Chats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(chat_id) REFERENCES chats(id)
                )
            """)

            # Create index on messages
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_chat_created 
                ON messages(chat_id, created_at)
            """)

            # Presets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    system_prompt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Preset fields table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preset_fields (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preset_id INTEGER NOT NULL,
                    field_name TEXT NOT NULL,
                    field_value TEXT NOT NULL,
                    FOREIGN KEY(preset_id) REFERENCES presets(id)
                )
            """)

            # Create index on preset_fields
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_preset_fields_preset 
                ON preset_fields(preset_id)
            """)

            # Preset runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS preset_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preset_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    response TEXT NOT NULL,
                    FOREIGN KEY(preset_id) REFERENCES presets(id)
                )
            """)

            self.conn.commit()
            logger.info("Database schema created successfully")

        except sqlite3.Error as e:
            logger.error(f"Failed to create schema: {e}")
            raise

    # Settings operations
    def get_settings(self) -> Settings:
        """Get application settings."""
        if not self.conn:
            return Settings.default()

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            rows = cursor.fetchall()

            settings_dict = dict(rows)
            return Settings(
                openai_api_key=settings_dict.get("openai_api_key", ""),
                openai_model=settings_dict.get("openai_model", "gpt-4o-mini"),
            )
        except sqlite3.Error as e:
            logger.error(f"Failed to get settings: {e}")
            return Settings.default()

    def save_settings(self, settings: Settings) -> None:
        """Save application settings."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("openai_api_key", settings.openai_api_key),
            )
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("openai_model", settings.openai_model),
            )
            self.conn.commit()
            logger.info("Settings saved successfully")
        except sqlite3.Error as e:
            logger.error(f"Failed to save settings: {e}")
            raise

    # Chat operations
    def create_chat(self, name: str) -> int:
        """Create a new chat and return its ID."""
        if not self.conn:
            raise RuntimeError("Database connection not available")

        try:
            cursor = self.conn.cursor()
            created_at = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO chats (name, created_at) VALUES (?, ?)",
                (name, created_at),
            )
            self.conn.commit()
            chat_id = cursor.lastrowid
            logger.info(f"Created chat {chat_id}: {name}")
            return chat_id
        except sqlite3.Error as e:
            logger.error(f"Failed to create chat: {e}")
            raise

    def get_all_chats(self) -> list[Chat]:
        """Get all chats ordered by creation date."""
        if not self.conn:
            return []

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, created_at FROM chats ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [Chat.from_row(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to get chats: {e}")
            return []

    def get_chat(self, chat_id: int) -> Chat | None:
        """Get a specific chat by ID."""
        if not self.conn:
            return None

        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, name, created_at FROM chats WHERE id = ?", (chat_id,))
            row = cursor.fetchone()
            return Chat.from_row(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get chat: {e}")
            return None

    def update_chat_name(self, chat_id: int, name: str) -> None:
        """Update chat name."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE chats SET name = ? WHERE id = ?", (name, chat_id))
            self.conn.commit()
            logger.info(f"Updated chat {chat_id} name to: {name}")
        except sqlite3.Error as e:
            logger.error(f"Failed to update chat name: {e}")
            raise

    def delete_chat(self, chat_id: int) -> None:
        """Delete a chat and all its messages."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
            cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
            self.conn.commit()
            logger.info(f"Deleted chat {chat_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete chat: {e}")
            raise

    # Message operations
    def add_message(self, chat_id: int, role: str, content: str) -> int:
        """Add a message to a chat and return its ID."""
        if not self.conn:
            raise RuntimeError("Database connection not available")

        try:
            cursor = self.conn.cursor()
            created_at = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (chat_id, role, content, created_at),
            )
            self.conn.commit()
            message_id = cursor.lastrowid
            logger.debug(f"Added message {message_id} to chat {chat_id}")
            return message_id
        except sqlite3.Error as e:
            logger.error(f"Failed to add message: {e}")
            raise

    def get_chat_messages(self, chat_id: int) -> list[Message]:
        """Get all messages for a chat ordered by creation date."""
        if not self.conn:
            return []

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT id, chat_id, role, content, created_at 
                FROM messages 
                WHERE chat_id = ? 
                ORDER BY created_at ASC
                """,
                (chat_id,),
            )
            rows = cursor.fetchall()
            return [Message.from_row(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to get messages: {e}")
            return []

    # Preset operations
    def create_preset(self, name: str, system_prompt: str = "") -> int:
        """Create a new preset and return its ID."""
        if not self.conn:
            raise RuntimeError("Database connection not available")

        try:
            cursor = self.conn.cursor()
            created_at = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO presets (name, system_prompt, created_at) VALUES (?, ?, ?)",
                (name, system_prompt, created_at),
            )
            self.conn.commit()
            preset_id = cursor.lastrowid
            logger.info(f"Created preset {preset_id}: {name}")
            return preset_id
        except sqlite3.Error as e:
            logger.error(f"Failed to create preset: {e}")
            raise

    def get_all_presets(self) -> list[Preset]:
        """Get all presets ordered by creation date."""
        if not self.conn:
            return []

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, system_prompt, created_at FROM presets ORDER BY created_at ASC"
            )
            rows = cursor.fetchall()
            return [Preset.from_row(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to get presets: {e}")
            return []

    def get_preset(self, preset_id: int) -> Preset | None:
        """Get a specific preset by ID."""
        if not self.conn:
            return None

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, name, system_prompt, created_at FROM presets WHERE id = ?",
                (preset_id,),
            )
            row = cursor.fetchone()
            return Preset.from_row(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Failed to get preset: {e}")
            return None

    def update_preset(self, preset_id: int, name: str, system_prompt: str) -> None:
        """Update preset name and system prompt."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE presets SET name = ?, system_prompt = ? WHERE id = ?",
                (name, system_prompt, preset_id),
            )
            self.conn.commit()
            logger.info(f"Updated preset {preset_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to update preset: {e}")
            raise

    def delete_preset(self, preset_id: int) -> None:
        """Delete a preset and all its fields and runs."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM preset_fields WHERE preset_id = ?", (preset_id,))
            cursor.execute("DELETE FROM preset_runs WHERE preset_id = ?", (preset_id,))
            cursor.execute("DELETE FROM presets WHERE id = ?", (preset_id,))
            self.conn.commit()
            logger.info(f"Deleted preset {preset_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete preset: {e}")
            raise

    # Preset field operations
    def add_preset_field(self, preset_id: int, field_name: str, field_value: str = "") -> int:
        """Add a field to a preset and return its ID."""
        if not self.conn:
            raise RuntimeError("Database connection not available")

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO preset_fields (preset_id, field_name, field_value) VALUES (?, ?, ?)",
                (preset_id, field_name, field_value),
            )
            self.conn.commit()
            field_id = cursor.lastrowid
            logger.debug(f"Added field {field_id} to preset {preset_id}")
            return field_id
        except sqlite3.Error as e:
            logger.error(f"Failed to add preset field: {e}")
            raise

    def get_preset_fields(self, preset_id: int) -> list[PresetField]:
        """Get all fields for a preset."""
        if not self.conn:
            return []

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT id, preset_id, field_name, field_value 
                FROM preset_fields 
                WHERE preset_id = ?
                ORDER BY id ASC
                """,
                (preset_id,),
            )
            rows = cursor.fetchall()
            return [PresetField.from_row(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to get preset fields: {e}")
            return []

    def update_preset_field(self, field_id: int, field_name: str, field_value: str) -> None:
        """Update a preset field."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE preset_fields SET field_name = ?, field_value = ? WHERE id = ?",
                (field_name, field_value, field_id),
            )
            self.conn.commit()
            logger.debug(f"Updated field {field_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to update preset field: {e}")
            raise

    def delete_preset_field(self, field_id: int) -> None:
        """Delete a preset field."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM preset_fields WHERE id = ?", (field_id,))
            self.conn.commit()
            logger.debug(f"Deleted field {field_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete preset field: {e}")
            raise

    def clear_preset_field_values(self, preset_id: int) -> None:
        """Clear all field values for a preset."""
        if not self.conn:
            return

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE preset_fields SET field_value = '' WHERE preset_id = ?",
                (preset_id,),
            )
            self.conn.commit()
            logger.info(f"Cleared field values for preset {preset_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to clear preset field values: {e}")
            raise

    # Preset run operations
    def add_preset_run(self, preset_id: int, response: str) -> int:
        """Add a preset run and return its ID."""
        if not self.conn:
            raise RuntimeError("Database connection not available")

        try:
            cursor = self.conn.cursor()
            created_at = datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO preset_runs (preset_id, created_at, response) VALUES (?, ?, ?)",
                (preset_id, created_at, response),
            )
            self.conn.commit()
            run_id = cursor.lastrowid
            logger.info(f"Added run {run_id} for preset {preset_id}")
            return run_id
        except sqlite3.Error as e:
            logger.error(f"Failed to add preset run: {e}")
            raise

    def get_preset_runs(self, preset_id: int) -> list[PresetRun]:
        """Get all runs for a preset ordered by creation date."""
        if not self.conn:
            return []

        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT id, preset_id, created_at, response 
                FROM preset_runs 
                WHERE preset_id = ? 
                ORDER BY created_at ASC
                """,
                (preset_id,),
            )
            rows = cursor.fetchall()
            return [PresetRun.from_row(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Failed to get preset runs: {e}")
            return []

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
