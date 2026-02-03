"""Utility functions for the AI Assistant application."""

import base64
import re
from pathlib import Path

import markdown
from loguru import logger

from app.enums import FileExtension, MessageRole


def read_text_file(file_path: str) -> str | None:
    """Read text file and return contents.

    Args:
        file_path: Path to the file.

    Returns:
        File contents or None if error occurs.
    """
    try:
        path = Path(file_path)

        # Check extension
        if path.suffix.lower() not in FileExtension.text_extensions():
            logger.warning(f"File extension {path.suffix} not allowed for text files")
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


def read_image_file(file_path: str) -> str | None:
    """Read image file and return base64 encoded string.

    Args:
        file_path: Path to the image file.

    Returns:
        Base64 encoded image string or None if error occurs.
    """
    try:
        path = Path(file_path)

        # Check extension
        if path.suffix.lower() not in FileExtension.image_extensions():
            logger.warning(f"File extension {path.suffix} not allowed for images")
            return None

        # Check file size (limit to 10MB for images)
        if path.stat().st_size > 10 * 1024 * 1024:
            logger.warning(f"Image file {file_path} too large (>10MB)")
            return None

        # Read and encode image
        with open(path, "rb") as f:
            image_data = f.read()
            return base64.b64encode(image_data).decode("utf-8")

    except Exception as e:
        logger.error(f"Error reading image file {file_path}: {e}")
        return None


def get_image_mime_type(file_path: str) -> str:
    """Get MIME type for image file.

    Args:
        file_path: Path to the image file.

    Returns:
        MIME type string.
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    mime_types = {
        FileExtension.PNG.value: "image/png",
        FileExtension.JPG.value: "image/jpeg",
        FileExtension.JPEG.value: "image/jpeg",
        FileExtension.GIF.value: "image/gif",
        FileExtension.WEBP.value: "image/webp",
    }

    return mime_types.get(extension, "image/jpeg")


def format_file_content(filename: str, content: str) -> str:
    """Format file content for insertion into message.

    Args:
        filename: Name of the file.
        content: File contents.

    Returns:
        Formatted string.
    """
    return f"\n\n--- File: {filename} ---\n{content}\n--- End of {filename} ---\n"


def format_image_content(filename: str) -> str:
    """Format image reference for insertion into message.

    Args:
        filename: Name of the image file.

    Returns:
        Formatted string.
    """
    return f"\n\n[Image: {filename}]\n"


def truncate_text(text: str, max_length: int = 40) -> str:
    """Truncate text to max length, trimming whitespace.

    Args:
        text: Text to truncate.
        max_length: Maximum length.

    Returns:
        Truncated text.
    """
    text = text.strip()
    if len(text) <= max_length:
        return text
    return text[:max_length].rstrip() + "..."


def validate_api_key(api_key: str) -> bool:
    """Validate OpenAI API key format.

    Args:
        api_key: API key to validate.

    Returns:
        True if valid format.
    """
    if not api_key:
        return False

    # Basic validation: should start with 'sk-' and have reasonable length
    return api_key.startswith("sk-") and len(api_key) > 20


def format_chat_messages_for_openai(
    messages: list[tuple[str, str]],
    system_message: str = "You are a helpful assistant.",
) -> list[dict[str, str]]:
    """Format chat messages for OpenAI API.

    Args:
        messages: List of (role, content) tuples.
        system_message: System message to prepend.

    Returns:
        List of message dicts for OpenAI API.
    """
    formatted: list[dict[str, str]] = [
        {"role": MessageRole.SYSTEM.value, "content": system_message}
    ]

    for role, content in messages:
        formatted.append({"role": role, "content": content})

    return formatted


def format_preset_messages_for_openai(
    system_prompt: str,
    fields: list[tuple[str, str]],
) -> list[dict[str, str]]:
    """Format preset fields as messages for OpenAI API.

    Args:
        system_prompt: System prompt for the preset.
        fields: List of (field_name, field_value) tuples.

    Returns:
        List of message dicts for OpenAI API.
    """
    # Build user message from fields
    field_parts = []
    for field_name, field_value in fields:
        field_parts.append(f"{field_name}:\n{field_value}\n")

    user_content = "\n".join(field_parts)

    return [
        {"role": MessageRole.SYSTEM.value, "content": system_prompt},
        {"role": MessageRole.USER.value, "content": user_content},
    ]


def render_markdown_to_text(content: str) -> str:
    """Convert markdown to formatted plain text for display in GUI.

    Args:
        content: Markdown content string.

    Returns:
        Formatted plain text with simple markdown rendering.
    """
    # Convert markdown to HTML first
    html = markdown.markdown(content, extensions=["fenced_code", "tables", "nl2br"])

    # Strip HTML tags for plain text display
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<p>", "", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<h1>(.*?)</h1>", r"# \1\n", text)
    text = re.sub(r"<h2>(.*?)</h2>", r"## \1\n", text)
    text = re.sub(r"<h3>(.*?)</h3>", r"### \1\n", text)
    text = re.sub(r"<h4>(.*?)</h4>", r"#### \1\n", text)
    text = re.sub(r"<h5>(.*?)</h5>", r"##### \1\n", text)
    text = re.sub(r"<h6>(.*?)</h6>", r"###### \1\n", text)
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text)
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text)
    text = re.sub(r"<pre><code[^>]*>(.*?)</code></pre>", r"```\n\1\n```", text, flags=re.DOTALL)
    text = re.sub(r"<ul>", "", text)
    text = re.sub(r"</ul>", "\n", text)
    text = re.sub(r"<ol>", "", text)
    text = re.sub(r"</ol>", "\n", text)
    text = re.sub(r"<li>(.*?)</li>", r"  • \1\n", text)
    text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)  # Remove any remaining HTML tags

    # Clean up excessive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()
