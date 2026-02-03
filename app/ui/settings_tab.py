"""Settings tab UI for the AI Assistant application."""

from typing import Any

import FreeSimpleGUI as sg
from loguru import logger

from ..db import Database
from ..models import Settings
from ..utils import OPENAI_MODELS, validate_api_key


def create_settings_tab(db: Database) -> list[list[sg.Element]]:
    """
    Create the settings tab layout.

    Args:
        db: Database instance

    Returns:
        Layout for settings tab
    """
    # Load current settings
    settings = db.get_settings()

    layout = [
        [sg.Text("OpenAI API Configuration", font=("Arial", 14, "bold"))],
        [sg.HorizontalSeparator()],
        [sg.Text("")],
        [
            sg.Text("API Key:", size=(15, 1)),
            sg.Input(
                default_text=settings.openai_api_key,
                key="-SETTINGS-API-KEY-",
                size=(50, 1),
                password_char="*",
            ),
        ],
        [sg.Text("")],
        [
            sg.Text("Model:", size=(15, 1)),
            sg.Combo(
                values=OPENAI_MODELS,
                default_value=settings.openai_model,
                key="-SETTINGS-MODEL-",
                size=(30, 1),
                readonly=True,
            ),
        ],
        [sg.Text("")],
        [
            sg.Button("Save Settings", key="-SETTINGS-SAVE-"),
            sg.Text("", key="-SETTINGS-STATUS-", size=(50, 1)),
        ],
    ]

    return layout


def handle_settings_events(
    event: str,
    values: dict[str, Any],
    window: sg.Window,
    db: Database,
) -> None:
    """
    Handle events in the settings tab.

    Args:
        event: Event string
        values: Values dictionary
        window: Main window
        db: Database instance
    """
    if event == "-SETTINGS-SAVE-":
        api_key = values["-SETTINGS-API-KEY-"].strip()
        model = values["-SETTINGS-MODEL-"]

        # Validate inputs
        if not api_key:
            sg.popup_error("API Key is required!", title="Validation Error")
            return

        if not model:
            sg.popup_error("Model selection is required!", title="Validation Error")
            return

        if not validate_api_key(api_key):
            sg.popup_error(
                "Invalid API Key format!\n\n"
                "API key should start with 'sk-' and be at least 20 characters long.",
                title="Validation Error",
            )
            return

        # Confirm if overwriting existing API key
        existing_settings = db.get_settings()
        if existing_settings.openai_api_key and existing_settings.openai_api_key != api_key:
            response = sg.popup_yes_no(
                "You are about to overwrite the existing API key.\n\nDo you want to continue?",
                title="Confirm API Key Change",
                default_button="No",
            )
            if response != "Yes":
                logger.info("API key change cancelled by user")
                return

        # Save settings
        try:
            settings = Settings(openai_api_key=api_key, openai_model=model)
            db.save_settings(settings)
            window["-SETTINGS-STATUS-"].update("✓ Settings saved successfully!", text_color="green")
            logger.info(f"Settings saved: model={model}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            sg.popup_error(f"Failed to save settings:\n{str(e)}", title="Error")
            window["-SETTINGS-STATUS-"].update("✗ Failed to save settings", text_color="red")
