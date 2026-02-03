"""Enumerations for the AI Assistant application."""

from enum import StrEnum


class MessageRole(StrEnum):
    """Message role in a conversation."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class FileExtension(StrEnum):
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


class OpenAIModel(StrEnum):
    """
    Practical, currently recommended OpenAI models (February 2026).

    - GPT-5 family is now the flagship & default for most serious use.
    - GPT-4o family is legacy → avoid for new projects (retiring soon in ChatGPT).
    - Removed speculative/future/deprecated names.
    """

    # Flagship / best quality (recommended for accuracy & complex tasks)
    GPT_5_2 = "gpt-5.2"  # Current top model – best for coding, agentic work, reasoning
    GPT_5 = "gpt-5"  # Still very capable (previous flagship)
    GPT_5_PRO = "gpt-5-pro"  # Enhanced version for Pro users (smarter, more precise)

    # Fast & cheap – high volume, agents, everyday use
    GPT_5_MINI = "gpt-5-mini"  # Best price/performance balance right now
    GPT_5_NANO = "gpt-5-nano"  # Fastest & cheapest variant

    @classmethod
    def recommended_default(cls) -> str:
        """What you should use as default in February 2026"""
        return cls.GPT_5_2.value  # Current best overall model

    @classmethod
    def get_all_values(cls) -> list[str]:
        """All still-realistic models (including short-term legacy)"""
        return [model.value for model in cls]
