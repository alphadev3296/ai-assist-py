"""Preset tab UI for the AI Assistant application."""

from typing import Any

import FreeSimpleGUI as sg
from loguru import logger

from ..db import Database
from ..models import Preset
from ..openai_client import StreamingClient, StreamQueue
from ..utils import format_preset_messages_for_openai


class PresetTabState:
    """State manager for preset tab."""

    def __init__(self, db: Database) -> None:
        """Initialize preset tab state."""
        self.db = db
        self.streaming_client: StreamingClient | None = None
        self.stream_queue: StreamQueue | None = None
        self.is_streaming: dict[int, bool] = {}  # preset_id -> is_streaming


def create_preset_tab(preset: Preset, db: Database) -> list[list[sg.Element]]:
    """
    Create a preset tab layout.

    Args:
        preset: Preset instance
        db: Database instance

    Returns:
        Layout for preset tab
    """
    # Load fields for this preset
    fields = db.get_preset_fields(preset.id)

    # Left panel - configuration
    left_panel = [
        [
            sg.Text(
                f"Preset: {preset.name}",
                font=("Arial", 12, "bold"),
                key=f"-PRESET-{preset.id}-TITLE-",
            )
        ],
        [
            sg.Button("Rename", key=f"-PRESET-{preset.id}-RENAME-", size=(10, 1)),
            sg.Button("Delete", key=f"-PRESET-{preset.id}-DELETE-", size=(10, 1)),
        ],
        [sg.HorizontalSeparator()],
        [sg.Text("System Prompt:")],
        [
            sg.Multiline(
                default_text=preset.system_prompt,
                size=(50, 5),
                key=f"-PRESET-{preset.id}-SYSPROMPT-",
                enable_events=True,
            )
        ],
        [sg.Text("Fields:", font=("Arial", 10, "bold"))],
    ]

    # Add existing fields
    for field in fields:
        left_panel.extend(
            [
                [sg.Text("Field Name:")],
                [
                    sg.Input(
                        default_text=field.field_name,
                        size=(48, 1),
                        key=f"-PRESET-{preset.id}-FIELD-{field.id}-NAME-",
                        enable_events=True,
                    ),
                    sg.Button(
                        "Remove",
                        key=f"-PRESET-{preset.id}-FIELD-{field.id}-REMOVE-",
                        size=(8, 1),
                    ),
                ],
                [sg.Text("Value:")],
                [
                    sg.Multiline(
                        default_text=field.field_value,
                        size=(50, 3),
                        key=f"-PRESET-{preset.id}-FIELD-{field.id}-VALUE-",
                        enable_events=True,
                    )
                ],
            ]
        )

    left_panel.extend(
        [
            [sg.Button("Add Field", key=f"-PRESET-{preset.id}-ADDFIELD-")],
            [sg.HorizontalSeparator()],
            [
                sg.Button("Clear Values", key=f"-PRESET-{preset.id}-CLEAR-"),
                sg.Button("Send", key=f"-PRESET-{preset.id}-SEND-"),
                sg.Button("Stop", key=f"-PRESET-{preset.id}-STOP-", disabled=True),
            ],
            [sg.Text("", key=f"-PRESET-{preset.id}-STATUS-", size=(48, 1))],
        ]
    )

    # Right panel - response history
    runs = db.get_preset_runs(preset.id)
    history_text = ""
    for i, run in enumerate(runs, 1):
        history_text += f"━━━ Run {i} ({run.created_at.strftime('%Y-%m-%d %H:%M:%S')}) ━━━\n"
        history_text += f"{run.response}\n\n"

    right_panel = [
        [sg.Text("Response History", font=("Arial", 12, "bold"))],
        [
            sg.Multiline(
                default_text=history_text,
                size=(60, 35),
                key=f"-PRESET-{preset.id}-HISTORY-",
                disabled=True,
                autoscroll=True,
            )
        ],
    ]

    layout = [
        [
            sg.Column(
                left_panel,
                vertical_alignment="top",
                scrollable=True,
                vertical_scroll_only=True,
                size=(550, 600),
            ),
            sg.VerticalSeparator(),
            sg.Column(right_panel, vertical_alignment="top"),
        ]
    ]

    return layout


def create_new_preset_tab() -> list[list[sg.Element]]:
    """
    Create the "+ New Preset" tab layout.

    Returns:
        Layout for new preset tab
    """
    layout = [
        [sg.Text("Create New Preset", font=("Arial", 14, "bold"))],
        [sg.Text("")],
        [sg.Text("Enter a name for the new preset:")],
        [sg.Input(key="-NEWPRESET-NAME-", size=(40, 1))],
        [sg.Text("")],
        [sg.Button("Create Preset", key="-NEWPRESET-CREATE-")],
    ]

    return layout


def refresh_preset_history(window: sg.Window, preset_id: int, db: Database) -> None:
    """
    Refresh the response history for a preset.

    Args:
        window: Main window
        preset_id: Preset ID
        db: Database instance
    """
    runs = db.get_preset_runs(preset_id)
    history_text = ""
    for i, run in enumerate(runs, 1):
        history_text += f"━━━ Run {i} ({run.created_at.strftime('%Y-%m-%d %H:%M:%S')}) ━━━\n"
        history_text += f"{run.response}\n\n"

    window[f"-PRESET-{preset_id}-HISTORY-"].update(history_text)


def handle_preset_events(
    event: str,
    values: dict[str, Any],
    window: sg.Window,
    state: PresetTabState,
    on_preset_change: Any,  # Callback to refresh tabs
) -> None:
    """
    Handle events in preset tabs.

    Args:
        event: Event string
        values: Values dictionary
        window: Main window
        state: Preset tab state
        on_preset_change: Callback when presets change (requires tab refresh)
    """
    # Check for streaming updates for any preset
    for preset_id, is_streaming in list(state.is_streaming.items()):
        if is_streaming and state.stream_queue:
            token = state.stream_queue.get_token()
            if token is not None:
                # Append token to history
                current = window[f"-PRESET-{preset_id}-HISTORY-"].get()
                window[f"-PRESET-{preset_id}-HISTORY-"].update(current + token)
            elif state.stream_queue.is_complete():
                # Streaming complete
                state.is_streaming[preset_id] = False
                window[f"-PRESET-{preset_id}-SEND-"].update(disabled=False)
                window[f"-PRESET-{preset_id}-STOP-"].update(disabled=True)
                window[f"-PRESET-{preset_id}-STATUS-"].update("", text_color="black")
            elif state.stream_queue.has_error():
                # Streaming error
                error = state.stream_queue.get_error()
                state.is_streaming[preset_id] = False
                window[f"-PRESET-{preset_id}-SEND-"].update(disabled=False)
                window[f"-PRESET-{preset_id}-STOP-"].update(disabled=True)
                window[f"-PRESET-{preset_id}-STATUS-"].update("Error occurred", text_color="red")
                sg.popup_error(f"Error during streaming:\n{str(error)}", title="Error")

    # Parse event to extract preset_id and action
    if event.startswith("-PRESET-") and event != "-NEWPRESET-NAME-":
        parts = event.split("-")
        if len(parts) >= 4:
            try:
                preset_id = int(parts[2])
            except ValueError:
                return

            # Handle system prompt updates
            if event.endswith("-SYSPROMPT-"):
                system_prompt = values[event]
                preset = state.db.get_preset(preset_id)
                if preset:
                    state.db.update_preset(preset_id, preset.name, system_prompt)
                    logger.debug(f"Updated system prompt for preset {preset_id}")

            # Handle field updates
            elif "-FIELD-" in event and event.endswith("-NAME-"):
                # Field name updated
                field_id = int(parts[4])
                field_name = values[event]
                value_key = f"-PRESET-{preset_id}-FIELD-{field_id}-VALUE-"
                field_value = values.get(value_key, "")
                state.db.update_preset_field(field_id, field_name, field_value)
                logger.debug(f"Updated field {field_id} name")

            elif "-FIELD-" in event and event.endswith("-VALUE-"):
                # Field value updated
                field_id = int(parts[4])
                field_value = values[event]
                name_key = f"-PRESET-{preset_id}-FIELD-{field_id}-NAME-"
                field_name = values.get(name_key, "")
                state.db.update_preset_field(field_id, field_name, field_value)
                logger.debug(f"Updated field {field_id} value")

            # Handle field removal
            elif "-FIELD-" in event and event.endswith("-REMOVE-"):
                field_id = int(parts[4])
                response = sg.popup_yes_no(
                    "Are you sure you want to remove this field?",
                    title="Confirm Remove",
                    default_button="No",
                )
                if response == "Yes":
                    state.db.delete_preset_field(field_id)
                    logger.info(f"Removed field {field_id}")
                    on_preset_change()  # Refresh tabs

            # Handle add field
            elif event.endswith("-ADDFIELD-"):
                field_name = sg.popup_get_text(
                    "Enter field name:",
                    title="Add Field",
                )
                if field_name and field_name.strip():
                    state.db.add_preset_field(preset_id, field_name.strip(), "")
                    logger.info(f"Added field to preset {preset_id}")
                    on_preset_change()  # Refresh tabs

            # Handle clear values
            elif event.endswith("-CLEAR-"):
                response = sg.popup_yes_no(
                    "Are you sure you want to clear all field values?",
                    title="Confirm Clear",
                    default_button="No",
                )
                if response == "Yes":
                    state.db.clear_preset_field_values(preset_id)
                    logger.info(f"Cleared field values for preset {preset_id}")
                    on_preset_change()  # Refresh tabs

            # Handle rename
            elif event.endswith("-RENAME-"):
                preset = state.db.get_preset(preset_id)
                if preset:
                    new_name = sg.popup_get_text(
                        "Enter new preset name:",
                        title="Rename Preset",
                        default_text=preset.name,
                    )
                    if new_name and new_name.strip():
                        state.db.update_preset(preset_id, new_name.strip(), preset.system_prompt)
                        logger.info(f"Renamed preset {preset_id}")
                        on_preset_change()  # Refresh tabs

            # Handle delete
            elif event.endswith("-DELETE-"):
                preset = state.db.get_preset(preset_id)
                if preset:
                    response = sg.popup_yes_no(
                        f"Are you sure you want to delete preset '{preset.name}'?\n\n"
                        f"This will also delete all fields and response history.",
                        title="Confirm Delete",
                        default_button="No",
                    )
                    if response == "Yes":
                        state.db.delete_preset(preset_id)
                        logger.info(f"Deleted preset {preset_id}")
                        on_preset_change()  # Refresh tabs

            # Handle send
            elif event.endswith("-SEND-"):
                # Get settings
                settings = state.db.get_settings()
                if not settings.openai_api_key:
                    sg.popup_error(
                        "Please configure your OpenAI API key in Settings!", title="Error"
                    )
                    return

                # Get preset and fields
                preset = state.db.get_preset(preset_id)
                if not preset:
                    return

                fields = state.db.get_preset_fields(preset_id)

                # Validate fields have values
                if not fields:
                    sg.popup_error("Please add at least one field to the preset!", title="Error")
                    return

                field_data = []
                for field in fields:
                    # Get current values from UI
                    name_key = f"-PRESET-{preset_id}-FIELD-{field.id}-NAME-"
                    value_key = f"-PRESET-{preset_id}-FIELD-{field.id}-VALUE-"
                    field_name = values.get(name_key, field.field_name)
                    field_value = values.get(value_key, field.field_value)
                    field_data.append((field_name, field_value))

                try:
                    # Prepare messages for OpenAI
                    system_prompt = values.get(
                        f"-PRESET-{preset_id}-SYSPROMPT-", preset.system_prompt
                    )
                    formatted_messages = format_preset_messages_for_openai(
                        system_prompt, field_data
                    )

                    # Setup streaming
                    state.streaming_client = StreamingClient(
                        api_key=settings.openai_api_key,
                        model=settings.openai_model,
                    )
                    state.stream_queue = StreamQueue()

                    # Add run header to history
                    current = window[f"-PRESET-{preset_id}-HISTORY-"].get()
                    from datetime import datetime

                    run_header = f"\n━━━ Run ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ━━━\n"
                    window[f"-PRESET-{preset_id}-HISTORY-"].update(current + run_header)

                    full_response = ""

                    def on_token(token: str) -> None:
                        nonlocal full_response
                        full_response += token
                        if state.stream_queue:
                            state.stream_queue.add_token(token)

                    def on_complete(response: str) -> None:
                        # Save preset run to database
                        state.db.add_preset_run(preset_id, full_response)
                        if state.stream_queue:
                            state.stream_queue.mark_complete()
                        logger.info(f"Preset {preset_id} run completed")

                    def on_error(error: Exception) -> None:
                        if state.stream_queue:
                            state.stream_queue.mark_error(error)

                    # Start streaming
                    state.streaming_client.stream_chat_completion(
                        messages=formatted_messages,
                        on_token=on_token,
                        on_complete=on_complete,
                        on_error=on_error,
                    )

                    state.is_streaming[preset_id] = True
                    window[f"-PRESET-{preset_id}-SEND-"].update(disabled=True)
                    window[f"-PRESET-{preset_id}-STOP-"].update(disabled=False)
                    window[f"-PRESET-{preset_id}-STATUS-"].update("Streaming...", text_color="blue")

                except Exception as e:
                    logger.error(f"Failed to send preset: {e}")
                    sg.popup_error(f"Failed to send preset:\n{str(e)}", title="Error")
                    window[f"-PRESET-{preset_id}-STATUS-"].update("Error", text_color="red")

            # Handle stop
            elif event.endswith("-STOP-"):
                if state.streaming_client:
                    state.streaming_client.stop_streaming()
                    state.is_streaming[preset_id] = False
                    window[f"-PRESET-{preset_id}-SEND-"].update(disabled=False)
                    window[f"-PRESET-{preset_id}-STOP-"].update(disabled=True)
                    window[f"-PRESET-{preset_id}-STATUS-"].update("Stopped", text_color="orange")
                    logger.info(f"Preset {preset_id} streaming stopped")

    # Handle new preset creation
    elif event == "-NEWPRESET-CREATE-":
        preset_name = values["-NEWPRESET-NAME-"].strip()
        if not preset_name:
            sg.popup_error("Please enter a preset name!", title="Error")
            return

        try:
            preset_id = state.db.create_preset(preset_name, "You are a helpful assistant.")
            logger.info(f"Created new preset: {preset_id}")
            window["-NEWPRESET-NAME-"].update("")
            on_preset_change()  # Refresh tabs
        except Exception as e:
            logger.error(f"Failed to create preset: {e}")
            sg.popup_error(f"Failed to create preset:\n{str(e)}", title="Error")
