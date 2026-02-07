"""Main GUI application for AI Assistant."""

from pathlib import Path

from loguru import logger
from nicegui import ui

from app.db import Database
from app.ui.chat_tab import ChatTab
from app.ui.preset_tab import PresetTab
from app.ui.settings_tab import SettingsTab


class AIAssistantApp:
    """Main application class."""

    def __init__(self) -> None:
        """Initialize the application."""
        # Setup logging
        self._setup_logging()

        # Initialize database
        self.db = Database()

        # Store tabs for updates
        self.chat_tab: ChatTab | None = None
        self.settings_tab: SettingsTab | None = None
        self.preset_tabs: dict[int, PresetTab] = {}
        self.tabs_container = None

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

    def refresh_presets(self) -> None:
        """Refresh preset tabs."""
        if self.tabs_container:
            self.build_ui()

    def build_ui(self) -> None:
        """Build the main user interface."""
        with ui.tabs().classes("w-full") as tabs:
            chat_tab_btn = ui.tab("Chat", icon="chat")
            settings_tab_btn = ui.tab("Settings", icon="settings")

            # Load presets
            presets = self.db.get_all_presets()
            preset_tab_btns = []
            for preset in presets:
                preset_tab_btns.append(ui.tab(preset.name, icon="description"))

            new_preset_tab_btn = ui.tab("+ New Preset", icon="add")

        with ui.tab_panels(tabs, value=chat_tab_btn).classes("w-full h-full"):
            # Chat tab
            with ui.tab_panel(chat_tab_btn).classes("w-full"):
                self.chat_tab = ChatTab(self.db)
                self.chat_tab.create_ui()

            # Settings tab
            with ui.tab_panel(settings_tab_btn).classes("w-full"):
                self.settings_tab = SettingsTab(self.db)
                self.settings_tab.create_ui()

            # Preset tabs
            for preset, tab_btn in zip(presets, preset_tab_btns, strict=True):
                with ui.tab_panel(tab_btn).classes("w-full"):
                    preset_tab = PresetTab(self.db, preset, self.refresh_presets)
                    preset_tab.create_ui()
                    self.preset_tabs[preset.id] = preset_tab

            # New preset tab
            with ui.tab_panel(new_preset_tab_btn).classes("w-full"):
                self.create_new_preset_tab()

    def create_new_preset_tab(self) -> None:
        """Create the new preset tab UI."""
        with ui.column().classes("w-full items-center p-8"):
            ui.markdown("### Create New Preset").classes("mb-4")

            preset_name_input = ui.input(
                label="Preset Name", placeholder="Enter preset name..."
            ).classes("w-96")

            async def create_preset() -> None:
                name = preset_name_input.value.strip()
                if not name:
                    ui.notify("Please enter a preset name!", type="warning")
                    return

                try:
                    preset_id = self.db.create_preset(name, "You are a helpful assistant.")
                    logger.info(f"Created new preset: {preset_id}")
                    ui.notify(f"Preset '{name}' created!", type="positive")
                    preset_name_input.value = ""
                    self.refresh_presets()
                except Exception as e:
                    logger.error(f"Failed to create preset: {e}")
                    ui.notify(f"Error: {str(e)}", type="negative")

            ui.button("Create Preset", on_click=create_preset, icon="add").classes("mt-4")

    def run(self) -> None:
        """Run the application."""
        logger.info("Starting NiceGUI application")

        # Build UI
        self.build_ui()

        # Run with native window mode
        ui.run(
            title="AI Assistant",
            native=True,
            window_size=(1400, 900),
            reload=False,
            show=True,
        )

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
