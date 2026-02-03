"""Data models for the AI Assistant application."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Chat:
    """Represents a chat conversation."""

    id: int
    name: str
    created_at: datetime

    @staticmethod
    def from_row(row: tuple[int, str, str]) -> "Chat":
        """Create Chat from database row."""
        return Chat(
            id=row[0],
            name=row[1],
            created_at=datetime.fromisoformat(row[2]),
        )


@dataclass
class Message:
    """Represents a message in a chat."""

    id: int
    chat_id: int
    role: str  # 'system', 'user', or 'assistant'
    content: str
    created_at: datetime

    @staticmethod
    def from_row(row: tuple[int, int, str, str, str]) -> "Message":
        """Create Message from database row."""
        return Message(
            id=row[0],
            chat_id=row[1],
            role=row[2],
            content=row[3],
            created_at=datetime.fromisoformat(row[4]),
        )


@dataclass
class Preset:
    """Represents a preset template."""

    id: int
    name: str
    system_prompt: str
    created_at: datetime

    @staticmethod
    def from_row(row: tuple[int, str, str, str]) -> "Preset":
        """Create Preset from database row."""
        return Preset(
            id=row[0],
            name=row[1],
            system_prompt=row[2],
            created_at=datetime.fromisoformat(row[3]),
        )


@dataclass
class PresetField:
    """Represents a field in a preset template."""

    id: int
    preset_id: int
    field_name: str
    field_value: str

    @staticmethod
    def from_row(row: tuple[int, int, str, str]) -> "PresetField":
        """Create PresetField from database row."""
        return PresetField(
            id=row[0],
            preset_id=row[1],
            field_name=row[2],
            field_value=row[3],
        )


@dataclass
class PresetRun:
    """Represents a run/execution of a preset."""

    id: int
    preset_id: int
    created_at: datetime
    response: str

    @staticmethod
    def from_row(row: tuple[int, int, str, str]) -> "PresetRun":
        """Create PresetRun from database row."""
        return PresetRun(
            id=row[0],
            preset_id=row[1],
            created_at=datetime.fromisoformat(row[2]),
            response=row[3],
        )


@dataclass
class Settings:
    """Application settings."""

    openai_api_key: str
    openai_model: str

    @staticmethod
    def default() -> "Settings":
        """Return default settings."""
        return Settings(
            openai_api_key="",
            openai_model="gpt-4o-mini",
        )
