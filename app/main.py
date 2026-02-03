"""Main GUI application for AI Assistant."""

from pathlib import Path

import FreeSimpleGUI as sg
from loguru import logger

from .db import Database
from .ui.chat_tab import ChatTabState, create_chat_tab, handle_chat_events
from .ui.preset_tab import (
    PresetTabState,
    create_new_preset_tab,
    create_preset_tab,
    handle_preset_events,
)
from .ui.settings_tab import create_settings_tab, handle_settings_events


class AIAssistantApp:
    """Main application class."""

    def __init__(self) -> None:
        """Initialize the application."""
        # Setup logging
        self._setup_logging()

        # Initialize database
        self.db = Database()

        # Initialize state
        self.chat_state = ChatTabState(self.db)
        self.preset_state = PresetTabState(self.db)

        # Create main window
        self.window: sg.Window | None = None
        self._create_window()

    def _setup_logging(self) -> None:
        """Setup application logging."""
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        logger.add(
            "logs/app.log",
            rotation="10 MB",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}",
        )
        logger.info("Application started")

    def _create_window(self) -> None:
        """Create the main application window."""
        sg.theme("LightBlue3")

        # Create tab groups
        chat_layout = create_chat_tab(self.db)
        settings_layout = create_settings_tab(self.db)

        # Load presets and create tabs
        presets = self.db.get_all_presets()
        preset_tabs = []

        for preset in presets:
            preset_layout = create_preset_tab(preset, self.db)
            preset_tabs.append(
                sg.Tab(
                    f"Preset: {preset.name}",
                    preset_layout,
                    key=f"-TAB-PRESET-{preset.id}-",
                )
            )

        # Add "New Preset" tab
        new_preset_layout = create_new_preset_tab()
        preset_tabs.append(sg.Tab("+ New Preset", new_preset_layout, key="-TAB-NEWPRESET-"))

        # Combine all tabs
        all_tabs = [
            sg.Tab("Chat", chat_layout, key="-TAB-CHAT-"),
            sg.Tab("Settings", settings_layout, key="-TAB-SETTINGS-"),
        ] + preset_tabs

        layout = [[sg.TabGroup([all_tabs], key="-TABGROUP-", enable_events=True)]]

        self.window = sg.Window(
            "AI Assistant",
            layout,
            size=(1200, 700),
            finalize=True,
            resizable=True,
        )

        logger.info("Main window created")

    def _refresh_window(self) -> None:
        """Refresh the entire window (recreate with updated presets)."""
        if self.window:
            self.window.close()
        self._create_window()
        logger.info("Window refreshed")

    def run(self) -> None:
        """Run the application main loop."""
        if not self.window:
            return

        logger.info("Entering main event loop")

        # Timer for checking streaming updates
        timeout = 100  # milliseconds

        while True:
            event, values = self.window.read(timeout=timeout)

            if event == sg.WIN_CLOSED:
                break

            # Handle chat tab events
            if event and (event.startswith("-CHAT-") or event in ["Rename Chat", "Delete Chat"]):
                handle_chat_events(event, values, self.window, self.chat_state)

            # Handle settings tab events
            elif event and event.startswith("-SETTINGS-"):
                handle_settings_events(event, values, self.window, self.db)

            # Handle preset tab events
            elif event and (event.startswith("-PRESET-") or event.startswith("-NEWPRESET-")):
                handle_preset_events(
                    event,
                    values,
                    self.window,
                    self.preset_state,
                    on_preset_change=self._refresh_window,
                )

            # Check for streaming updates even without explicit events
            if self.chat_state.is_streaming:
                handle_chat_events("", values, self.window, self.chat_state)

            for preset_id in list(self.preset_state.is_streaming.keys()):
                if self.preset_state.is_streaming.get(preset_id):
                    handle_preset_events(
                        "", values, self.window, self.preset_state, self._refresh_window
                    )

        logger.info("Application closing")
        self.window.close()
        self.db.close()

    def __del__(self) -> None:
        """Cleanup on deletion."""
        if hasattr(self, "db"):
            self.db.close()


def main() -> None:
    """Main entry point."""
    app = AIAssistantApp()
    app.run()


if __name__ == "__main__":
    main()
