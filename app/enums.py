"""Enumerations for the AI Assistant application."""

from enum import Enum


class MessageRole(str, Enum):
    """Message role in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class FileExtension(str, Enum):
    """Allowed file extensions for upload."""

    TXT = ".txt"
    MD = ".md"
    PY = ".py"
    JSON = ".json"
    PNG = ".png"
    JPG = ".jpg"
    JPEG = ".jpeg"
    GIF = ".gif"
    WEBP = ".webp"

    @classmethod
    def text_extensions(cls) -> set[str]:
        """Get text file extensions."""
        return {cls.TXT.value, cls.MD.value, cls.PY.value, cls.JSON.value}

    @classmethod
    def image_extensions(cls) -> set[str]:
        """Get image file extensions."""
        return {cls.PNG.value, cls.JPG.value, cls.JPEG.value, cls.GIF.value, cls.WEBP.value}

    @classmethod
    def all_extensions(cls) -> set[str]:
        """Get all allowed extensions."""
        return cls.text_extensions() | cls.image_extensions()


class OpenAIModel(str, Enum):
    """Available OpenAI models."""

    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_4 = "gpt-4"
    GPT_35_TURBO = "gpt-3.5-turbo"

    @classmethod
    def get_all_values(cls) -> list[str]:
        """Get all model values as a list."""
        return [model.value for model in cls]
