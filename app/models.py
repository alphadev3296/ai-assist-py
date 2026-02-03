"""Data models for the AI Assistant application."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from .enums import MessageRole, OpenAIModel


class Chat(BaseModel):
    """Represents a chat conversation."""

    id: int
    name: str
    created_at: datetime


class Message(BaseModel):
    """Represents a message in a chat."""

    id: int
    chat_id: int
    role: MessageRole
    content: str
    created_at: datetime


class Preset(BaseModel):
    """Represents a preset template."""

    id: int
    name: str
    system_prompt: str
    created_at: datetime


class PresetField(BaseModel):
    """Represents a field in a preset template."""

    id: int
    preset_id: int
    field_name: str
    field_value: str = ""


class PresetRun(BaseModel):
    """Represents a run/execution of a preset."""

    id: int
    preset_id: int
    created_at: datetime
    response: str


class Settings(BaseModel):
    """Application settings."""

    openai_api_key: str = Field(default="")
    openai_model: str = Field(default=OpenAIModel.GPT_4O_MINI.value)

    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format if provided."""
        if v and not v.startswith("sk-"):
            raise ValueError("API key must start with 'sk-'")
        return v

    @field_validator("openai_model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model is in allowed list."""
        if v not in OpenAIModel.get_all_values():
            raise ValueError(f"Model must be one of {OpenAIModel.get_all_values()}")
        return v
