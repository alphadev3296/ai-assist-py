"""Settings tab UI for the AI Assistant application."""

from typing import Any

from loguru import logger
from nicegui import ui

from app.db import Database
from app.enums import OpenAIModel
from app.models import Settings
from app.utils import validate_api_key


class SettingsTab:
    """Settings tab component."""

    def __init__(self, db: Database) -> None:
        """Initialize settings tab.

        Args:
            db: Database instance.
        """
        self.db = db
        self.api_key_input: Any = None
        self.model_select: Any = None
        self.status_label: Any = None

    def create_ui(self) -> None:
        """Create the settings tab layout."""
        settings = self.db.get_settings()

        with ui.column().classes("w-full max-w-2xl mx-auto p-8"):
            ui.markdown("## OpenAI API Configuration").classes("mb-4")

            ui.separator().classes("mb-6")

            self.api_key_input = ui.input(
                label="API Key",
                value=settings.openai_api_key,
                password=True,
                password_toggle_button=True,
            ).classes("w-full mb-4")

            self.model_select = ui.select(
                label="Model", options=OpenAIModel.get_all_values(), value=settings.openai_model
            ).classes("w-full mb-6")

            with ui.row().classes("gap-2 items-center"):
                ui.button("Save Settings", on_click=self.save_settings, icon="save").props(
                    "color=primary"
                )

                self.status_label = ui.label("").classes("ml-4")

    async def save_settings(self) -> None:
        """Save the settings."""
        if self.api_key_input is None or self.model_select is None:
            return
        api_key = self.api_key_input.value.strip()
        model = self.model_select.value

        # Validate inputs
        if not api_key:
            ui.notify("API Key is required!", type="warning")
            return

        if not model:
            ui.notify("Model selection is required!", type="warning")
            return

        if not validate_api_key(api_key):
            ui.notify(
                "Invalid API Key format! Key should start with 'sk-' and be "
                "at least 20 characters long.",
                type="negative",
            )
            return

        # Confirm if overwriting existing API key
        existing_settings = self.db.get_settings()
        if existing_settings.openai_api_key and existing_settings.openai_api_key != api_key:
            # Use dialog for confirmation
            with ui.dialog() as dialog, ui.card():
                ui.markdown("### Confirm API Key Change")
                ui.label("You are about to overwrite the existing API key.")
                ui.label("Do you want to continue?")

                async def confirm_save() -> None:
                    await self.perform_save(api_key, model)
                    dialog.close()

                with ui.row():
                    ui.button("Cancel", on_click=dialog.close)
                    ui.button("Continue", on_click=confirm_save).props("color=primary")

            dialog.open()
        else:
            await self.perform_save(api_key, model)

    async def perform_save(self, api_key: str, model: str) -> None:
        """Perform the actual save operation."""
        try:
            settings = Settings(openai_api_key=api_key, openai_model=model)
            self.db.save_settings(settings)
            if self.status_label is not None:
                self.status_label.set_text("✓ Settings saved successfully!")
                self.status_label.style("color: green")
            ui.notify("Settings saved!", type="positive")
            logger.info(f"Settings saved: model={model}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            if self.status_label is not None:
                self.status_label.set_text("✗ Failed to save settings")
                self.status_label.style("color: red")
            ui.notify(f"Error: {str(e)}", type="negative")
