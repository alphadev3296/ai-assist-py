"""Preset tab UI for the AI Assistant application."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from loguru import logger
from nicegui import ui

from app.db import Database
from app.models import Preset
from app.openai_client import StreamingClient, StreamQueue
from app.utils import format_preset_messages_for_openai


class PresetTab:
    """Preset tab component."""

    def __init__(
        self, db: Database, preset: Preset, on_change_callback: Callable[[], None]
    ) -> None:
        """Initialize preset tab.

        Args:
            db: Database instance.
            preset: Preset model.
            on_change_callback: Callback when preset is modified/deleted.
        """
        self.db = db
        self.preset = preset
        self.on_change_callback = on_change_callback
        self.streaming_client: StreamingClient | None = None
        self.stream_queue: StreamQueue | None = None
        self.is_streaming = False

        # UI components
        self.system_prompt_input: Any = None
        self.history_area: Any = None
        self.send_button: Any = None
        self.stop_button: Any = None
        self.status_label: Any = None
        self.fields_container: Any = None
        self.field_inputs: dict[int, dict[str, Any]] = {}

    def create_ui(self) -> None:
        """Create the preset tab layout."""
        with ui.row().classes("w-full h-full gap-2"):
            # Left panel - configuration
            with ui.column().classes("w-1/2 h-full"):
                ui.markdown(f"**Preset: {self.preset.name}**").classes("mb-2")

                with ui.row().classes("gap-2 mb-4"):
                    ui.button("Rename", on_click=self.rename_preset, icon="edit")
                    ui.button("Delete", on_click=self.delete_preset, icon="delete")

                ui.label("System Prompt:").classes("font-bold mt-2")
                self.system_prompt_input = (
                    ui.textarea(
                        value=self.preset.system_prompt, on_change=self.update_system_prompt
                    )
                    .classes("w-full")
                    .props("outlined rows=3")
                )

                ui.label("Fields:").classes("font-bold mt-4")

                # Fields container with scroll
                with ui.scroll_area().classes(
                    "w-full h-96 border rounded p-2"
                ) as self.fields_container:
                    self.render_fields()

                ui.button("Add Field", on_click=self.add_field, icon="add").classes("mt-2")

                ui.separator().classes("my-4")

                with ui.row().classes("gap-2 items-center"):
                    ui.button("Clear Values", on_click=self.clear_values, icon="clear")
                    self.send_button = ui.button(
                        "Send", on_click=self.send_preset, icon="send"
                    ).props("color=primary")
                    self.stop_button = ui.button(
                        "Stop", on_click=self.stop_streaming, icon="stop"
                    ).props("color=negative")
                    self.stop_button.set_enabled(False)

                self.status_label = ui.label("").classes("mt-2")

            # Right panel - response history
            with ui.column().classes("flex-1 h-full"):
                ui.markdown("**Response History**").classes("mb-2")

                with ui.scroll_area().classes("w-full h-full border rounded p-2"):
                    self.history_area = ui.html("")

        # Load initial history
        self.refresh_history()

        # Start background task
        ui.timer(0.1, self.check_streaming)

    def render_fields(self) -> None:
        """Render all preset fields."""
        fields = self.db.get_preset_fields(self.preset.id)

        with self.fields_container:
            self.fields_container.clear()
            self.field_inputs.clear()

            for field in fields:
                with ui.card().classes("w-full p-2 mb-2"):
                    field_name_input = ui.input(
                        label="Field Name",
                        value=field.field_name,
                        on_change=lambda e, fid=field.id: self.update_field_name(fid, e.value),
                    ).classes("w-full")

                    field_value_input = (
                        ui.textarea(
                            label="Value",
                            value=field.field_value,
                            on_change=lambda e, fid=field.id: self.update_field_value(fid, e.value),
                        )
                        .classes("w-full")
                        .props("outlined rows=2")
                    )

                    ui.button(
                        "Remove",
                        on_click=lambda fid=field.id: self.remove_field(fid),
                        icon="delete",
                    ).props("color=negative size=sm")

                    self.field_inputs[field.id] = {
                        "name": field_name_input,
                        "value": field_value_input,
                    }

    def update_system_prompt(self, e: Any) -> None:
        """Update system prompt in database."""
        if self.system_prompt_input is None:
            return
        new_prompt = self.system_prompt_input.value
        self.db.update_preset(self.preset.id, self.preset.name, new_prompt)
        logger.debug(f"Updated system prompt for preset {self.preset.id}")

    def update_field_name(self, field_id: int, new_name: str) -> None:
        """Update field name."""
        field = self.db.get_preset_field(field_id)
        if field:
            self.db.update_preset_field(field_id, new_name, field.field_value)
            logger.debug(f"Updated field {field_id} name")

    def update_field_value(self, field_id: int, new_value: str) -> None:
        """Update field value."""
        field = self.db.get_preset_field(field_id)
        if field:
            self.db.update_preset_field(field_id, field.field_name, new_value)
            logger.debug(f"Updated field {field_id} value")

    async def add_field(self) -> None:
        """Add a new field."""
        with ui.dialog() as dialog, ui.card():
            ui.markdown("### Add Field")
            field_name_input = ui.input(label="Field Name").classes("w-96")

            async def confirm_add() -> None:
                if field_name_input.value.strip():
                    self.db.add_preset_field(self.preset.id, field_name_input.value.strip(), "")
                    logger.info(f"Added field to preset {self.preset.id}")
                    self.render_fields()
                    dialog.close()

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Add", on_click=confirm_add).props("color=primary")

        dialog.open()

    async def remove_field(self, field_id: int) -> None:
        """Remove a field."""
        with ui.dialog() as dialog, ui.card():
            ui.markdown("### Confirm Remove")
            ui.label("Remove this field?")

            async def confirm_remove() -> None:
                self.db.delete_preset_field(field_id)
                logger.info(f"Removed field {field_id}")
                self.render_fields()
                dialog.close()

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Remove", on_click=confirm_remove).props("color=negative")

        dialog.open()

    async def clear_values(self) -> None:
        """Clear all field values."""
        with ui.dialog() as dialog, ui.card():
            ui.markdown("### Confirm Clear")
            ui.label("Clear all field values?")

            async def confirm_clear() -> None:
                self.db.clear_preset_field_values(self.preset.id)
                logger.info(f"Cleared field values for preset {self.preset.id}")
                self.render_fields()
                dialog.close()

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Clear", on_click=confirm_clear).props("color=primary")

        dialog.open()

    async def rename_preset(self) -> None:
        """Rename the preset."""
        with ui.dialog() as dialog, ui.card():
            ui.markdown("### Rename Preset")
            new_name_input = ui.input(label="New Name", value=self.preset.name).classes("w-96")

            async def confirm_rename() -> None:
                if new_name_input.value.strip():
                    self.db.update_preset(
                        self.preset.id, new_name_input.value.strip(), self.preset.system_prompt
                    )
                    logger.info(f"Renamed preset {self.preset.id}")
                    dialog.close()
                    self.on_change_callback()

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Rename", on_click=confirm_rename).props("color=primary")

        dialog.open()

    async def delete_preset(self) -> None:
        """Delete the preset."""
        with ui.dialog() as dialog, ui.card():
            ui.markdown("### Confirm Delete")
            ui.label(f"Delete preset '{self.preset.name}'?")
            ui.label("This will delete all fields and history.")

            async def confirm_delete() -> None:
                self.db.delete_preset(self.preset.id)
                logger.info(f"Deleted preset {self.preset.id}")
                dialog.close()
                self.on_change_callback()

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Delete", on_click=confirm_delete).props("color=negative")

        dialog.open()

    def refresh_history(self) -> None:
        """Refresh the response history display."""
        runs = self.db.get_preset_runs(self.preset.id)
        history_html = ""

        for i, run in enumerate(runs, 1):
            history_html += "<div style='margin-bottom: 1.5em;'>"
            run_timestamp = run.created_at.strftime("%Y-%m-%d %H:%M:%S")
            history_html += f"<strong>━━━ Run {i} ({run_timestamp}) ━━━</strong><br>"
            from markdown import markdown

            rendered = markdown(run.response)
            history_html += f"{rendered}"
            history_html += "</div>"

        if self.history_area is not None:
            self.history_area.set_content(history_html)

    async def check_streaming(self) -> None:
        """Check for streaming updates."""
        if not self.is_streaming or not self.stream_queue:
            return

        token = self.stream_queue.get_token()
        if token is not None:
            # Append token
            if self.history_area is not None:
                current_html = self.history_area.content
                self.history_area.set_content(current_html + token.replace("\n", "<br>"))
        elif self.stream_queue.is_complete():
            # Streaming complete
            self.is_streaming = False
            if self.send_button is not None:
                self.send_button.set_enabled(True)
            if self.stop_button is not None:
                self.stop_button.set_enabled(False)
            if self.status_label is not None:
                self.status_label.set_text("")
            self.refresh_history()
        elif self.stream_queue.has_error():
            # Streaming error
            error = self.stream_queue.get_error()
            self.is_streaming = False
            if self.send_button is not None:
                self.send_button.set_enabled(True)
            if self.stop_button is not None:
                self.stop_button.set_enabled(False)
            if self.status_label is not None:
                self.status_label.set_text("Error occurred")
                self.status_label.style("color: red")
            ui.notify(f"Error: {str(error)}", type="negative")

    async def send_preset(self) -> None:
        """Send preset to OpenAI."""
        settings = self.db.get_settings()
        if not settings.openai_api_key:
            ui.notify("Please configure your OpenAI API key in Settings!", type="warning")
            return

        fields = self.db.get_preset_fields(self.preset.id)
        if not fields:
            ui.notify("Please add at least one field!", type="warning")
            return

        # Get current field values from UI
        field_data = []
        for field in fields:
            if field.id in self.field_inputs:
                name = self.field_inputs[field.id]["name"].value
                value = self.field_inputs[field.id]["value"].value
                field_data.append((name, value))
            else:
                field_data.append((field.field_name, field.field_value))

        try:
            # Prepare messages
            if self.system_prompt_input is None:
                return
            system_prompt = self.system_prompt_input.value
            formatted_messages = format_preset_messages_for_openai(system_prompt, field_data)

            # Setup streaming
            self.streaming_client = StreamingClient(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
            self.stream_queue = StreamQueue()

            # Add run header
            if self.history_area is not None:
                current_html = self.history_area.content
                run_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                run_header = (
                    f"<div style='margin-bottom: 1.5em;'>"
                    f"<strong>━━━ Run ({run_timestamp}) ━━━</strong><br>"
                )
                self.history_area.set_content(current_html + run_header)

            full_response = ""

            def on_token(token: str) -> None:
                nonlocal full_response
                full_response += token
                if self.stream_queue:
                    self.stream_queue.add_token(token)

            def on_complete(response: str) -> None:
                self.db.add_preset_run(self.preset.id, full_response)
                if self.stream_queue:
                    self.stream_queue.mark_complete()
                logger.info(f"Preset {self.preset.id} run completed")

            def on_error(error: Exception) -> None:
                if self.stream_queue:
                    self.stream_queue.mark_error(error)

            # Start streaming
            self.streaming_client.stream_chat_completion(
                messages=formatted_messages,
                on_token=on_token,
                on_complete=on_complete,
                on_error=on_error,
            )

            self.is_streaming = True
            if self.send_button is not None:
                self.send_button.set_enabled(False)
            if self.stop_button is not None:
                self.stop_button.set_enabled(True)
            if self.status_label is not None:
                self.status_label.set_text("Streaming...")
                self.status_label.style("color: blue")

        except Exception as e:
            logger.error(f"Failed to send preset: {e}")
            ui.notify(f"Error: {str(e)}", type="negative")
            if self.status_label is not None:
                self.status_label.set_text("Error")
                self.status_label.style("color: red")

    async def stop_streaming(self) -> None:
        """Stop the streaming."""
        if self.streaming_client:
            self.streaming_client.stop_streaming()
            self.is_streaming = False
            if self.send_button is not None:
                self.send_button.set_enabled(True)
            if self.stop_button is not None:
                self.stop_button.set_enabled(False)
            if self.status_label is not None:
                self.status_label.set_text("Stopped")
                self.status_label.style("color: orange")
            logger.info(f"Preset {self.preset.id} streaming stopped")
