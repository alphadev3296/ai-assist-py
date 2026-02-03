"""UI package for the AI Assistant application."""

from app.ui.chat_tab import create_chat_tab
from app.ui.preset_tab import create_preset_tab
from app.ui.settings_tab import create_settings_tab

__all__ = ["create_chat_tab", "create_settings_tab", "create_preset_tab"]
