"""Data models for the AI Assistant application."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.enums import MessageRole, OpenAIModel


class Chat(BaseModel):
    """Represents a chat conversation."""

    id: Annotated[int, Field(description="Unique identifier for the chat")]
    name: Annotated[str, Field(description="Name/title of the chat conversation")]
    created_at: Annotated[datetime, Field(description="Timestamp when chat was created")]


class Message(BaseModel):
    """Represents a message in a chat."""

    id: Annotated[int, Field(description="Unique identifier for the message")]
    chat_id: Annotated[int, Field(description="ID of the chat this message belongs to")]
    role: Annotated[
        MessageRole, Field(description="Role of the message sender (system/user/assistant)")
    ]
    content: Annotated[str, Field(description="Text content of the message")]
    created_at: Annotated[datetime, Field(description="Timestamp when message was created")]


class Preset(BaseModel):
    """Represents a preset template."""

    id: Annotated[int, Field(description="Unique identifier for the preset")]
    name: Annotated[str, Field(description="Name of the preset template")]
    system_prompt: Annotated[str, Field(description="System prompt text for the preset")]
    created_at: Annotated[datetime, Field(description="Timestamp when preset was created")]


class PresetField(BaseModel):
    """Represents a field in a preset template."""

    id: Annotated[int, Field(description="Unique identifier for the field")]
    preset_id: Annotated[int, Field(description="ID of the preset this field belongs to")]
    field_name: Annotated[str, Field(description="Name of the field")]
    field_value: Annotated[str, Field(default="", description="Current value of the field")]


class PresetRun(BaseModel):
    """Represents a run/execution of a preset."""

    id: Annotated[int, Field(description="Unique identifier for the run")]
    preset_id: Annotated[int, Field(description="ID of the preset that was executed")]
    created_at: Annotated[datetime, Field(description="Timestamp when preset was run")]
    response: Annotated[str, Field(description="Response text from the OpenAI API")]


class Settings(BaseModel):
    """Application settings."""

    openai_api_key: Annotated[
        str,
        Field(default="", description="OpenAI API key for authentication"),
    ]
    openai_model: Annotated[
        str,
        Field(
            default=OpenAIModel.GPT_4O_MINI.value,
            description="OpenAI model to use for completions",
        ),
    ]

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
