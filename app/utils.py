"""Utility functions for the AI Assistant application."""

from pathlib import Path

from loguru import logger

# Allowed file extensions for upload
ALLOWED_EXTENSIONS = {".txt", ".md", ".py", ".json"}

# OpenAI model options
OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    "gpt-3.5-turbo",
]


def read_text_file(file_path: str) -> str | None:
    """
    Read text file and return contents.

    Args:
        file_path: Path to the file

    Returns:
        File contents or None if error occurs
    """
    try:
        path = Path(file_path)

        # Check extension
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            logger.warning(f"File extension {path.suffix} not allowed")
            return None

        # Check file size (limit to 1MB)
        if path.stat().st_size > 1024 * 1024:
            logger.warning(f"File {file_path} too large (>1MB)")
            return None

        # Read file
        with open(path, encoding="utf-8") as f:
            return f.read()

    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def format_file_content(filename: str, content: str) -> str:
    """
    Format file content for insertion into message.

    Args:
        filename: Name of the file
        content: File contents

    Returns:
        Formatted string
    """
    return f"\n\n--- File: {filename} ---\n{content}\n--- End of {filename} ---\n"


def truncate_text(text: str, max_length: int = 40) -> str:
    """
    Truncate text to max length, trimming whitespace.

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def validate_api_key(api_key: str) -> bool:
    """
    Validate OpenAI API key format.

    Args:
        api_key: API key to validate

    Returns:
        True if valid format
    """
    if not api_key:
        return False

    # Basic validation: should start with 'sk-' and have reasonable length
    return api_key.startswith("sk-") and len(api_key) > 20


def format_chat_messages_for_openai(
    messages: list[tuple[str, str]],
    system_message: str = "You are a helpful assistant.",
) -> list[dict[str, str]]:
    """
    Format chat messages for OpenAI API.

    Args:
        messages: List of (role, content) tuples
        system_message: System message to prepend

    Returns:
        List of message dicts for OpenAI API
    """
    formatted: list[dict[str, str]] = [{"role": "system", "content": system_message}]

    for role, content in messages:
        formatted.append({"role": role, "content": content})

    return formatted


def format_preset_messages_for_openai(
    system_prompt: str,
    fields: list[tuple[str, str]],
) -> list[dict[str, str]]:
    """
    Format preset fields as messages for OpenAI API.

    Args:
        system_prompt: System prompt for the preset
        fields: List of (field_name, field_value) tuples

    Returns:
        List of message dicts for OpenAI API
    """
    # Build user message from fields
    field_parts = []
    for field_name, field_value in fields:
        field_parts.append(f"{field_name}:\n{field_value}\n")

    user_content = "\n".join(field_parts)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
