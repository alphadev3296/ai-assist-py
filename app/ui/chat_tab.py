"""Chat tab UI for the AI Assistant application."""

from pathlib import Path
from typing import Any

from loguru import logger
from nicegui import events, ui

from app.db import Database
from app.enums import FileExtension, MessageRole
from app.openai_client import StreamingClient, StreamQueue
from app.utils import (
    format_chat_messages_for_openai,
    format_file_content,
    format_image_content,
    truncate_text,
)


class ChatTab:
    """Chat tab component."""

    def __init__(self, db: Database) -> None:
        """Initialize chat tab.

        Args:
            db: Database instance.
        """
        self.db = db
        self.current_chat_id: int | None = None
        self.streaming_client: StreamingClient | None = None
        self.stream_queue: StreamQueue | None = None
        self.is_streaming = False

        # UI components
        self.chat_list: Any = None
        self.chat_history: Any = None
        self.chat_input: Any = None
        self.send_button: Any = None
        self.stop_button: Any = None
        self.status_label: Any = None

    def create_ui(self) -> None:
        """Create the chat tab layout."""
        with ui.row().classes("w-full h-full gap-2"):
            # Left panel - chat list
            with ui.column().classes("w-64 h-full"):
                ui.markdown("**Chats**").classes("mb-2")

                chats = self.db.get_all_chats()
                chat_names = [chat.name for chat in chats]

                self.chat_list = ui.select(
                    options=chat_names, label="Select Chat", on_change=self.on_chat_selected
                ).classes("w-full")

                ui.button("New Chat", on_click=self.create_new_chat, icon="add").classes(
                    "w-full mt-2"
                )

                with ui.row().classes("w-full mt-2 gap-1"):
                    ui.button("Rename", on_click=self.rename_chat, icon="edit").classes("flex-1")
                    ui.button("Delete", on_click=self.delete_chat, icon="delete").classes("flex-1")

            # Right panel - messages and input
            with ui.column().classes("flex-1 h-full"):
                ui.markdown("**Message History**").classes("mb-2")

                # Chat history (scrollable)
                with ui.scroll_area().classes("w-full h-96 border rounded p-2"):
                    self.chat_history = ui.html("").classes("w-full")

                ui.label("Your Message:").classes("mt-4")

                self.chat_input = (
                    ui.textarea(placeholder="Type your message... (Ctrl+Enter to send)")
                    .classes("w-full")
                    .props("outlined rows=4")
                )

                # Handle Ctrl+Enter
                self.chat_input.on("keydown.ctrl.enter", self.send_message)

                with ui.row().classes("w-full gap-2 mt-2 items-center"):
                    ui.button("Upload File", on_click=self.upload_file, icon="upload_file")
                    self.send_button = ui.button(
                        "Send", on_click=self.send_message, icon="send"
                    ).props("color=primary")
                    self.stop_button = ui.button(
                        "Stop", on_click=self.stop_streaming, icon="stop"
                    ).props("color=negative")
                    self.stop_button.set_enabled(False)

                    self.status_label = ui.label("").classes("ml-4")

        # Start background task to check streaming
        ui.timer(0.1, self.check_streaming)

    async def check_streaming(self) -> None:
        """Check for streaming updates."""
        if not self.is_streaming or not self.stream_queue:
            return

        token = self.stream_queue.get_token()
        if token is not None:
            # Append token to history
            current_html = self.chat_history.content
            self.chat_history.set_content(current_html + token.replace("\n", "<br>"))
        elif self.stream_queue.is_complete():
            # Streaming complete
            self.is_streaming = False
            self.send_button.set_enabled(True)
            self.stop_button.set_enabled(False)
            self.status_label.set_text("")
            # Reload messages with proper formatting
            if self.current_chat_id:
                await self.load_chat_messages(self.current_chat_id)
        elif self.stream_queue.has_error():
            # Streaming error
            error = self.stream_queue.get_error()
            self.is_streaming = False
            self.send_button.set_enabled(True)
            self.stop_button.set_enabled(False)
            self.status_label.set_text("Error occurred").style("color: red")
            ui.notify(f"Error: {str(error)}", type="negative")

    async def create_new_chat(self) -> None:
        """Create a new chat."""
        try:
            chat_id = self.db.create_chat("New Chat")
            await self.refresh_chat_list(chat_id)
            self.current_chat_id = chat_id
            self.chat_history.set_content("")
            self.chat_input.value = ""
            self.status_label.set_text("New chat created").style("color: green")
            logger.info(f"Created new chat: {chat_id}")
        except Exception as e:
            logger.error(f"Failed to create chat: {e}")
            ui.notify(f"Error: {str(e)}", type="negative")

    async def refresh_chat_list(self, selected_chat_id: int | None = None) -> None:
        """Refresh the chat list."""
        chats = self.db.get_all_chats()
        chat_names = [chat.name for chat in chats]
        self.chat_list.set_options(chat_names)

        if selected_chat_id:
            for chat in chats:
                if chat.id == selected_chat_id:
                    self.chat_list.set_value(chat.name)
                    break

    async def on_chat_selected(self) -> None:
        """Handle chat selection."""
        selected = self.chat_list.value
        if not selected:
            return

        chats = self.db.get_all_chats()
        for chat in chats:
            if chat.name == selected:
                self.current_chat_id = chat.id
                await self.load_chat_messages(chat.id)
                self.status_label.set_text("")
                logger.info(f"Loaded chat: {chat.id}")
                break

    async def load_chat_messages(self, chat_id: int) -> None:
        """Load and display messages for a chat."""
        messages = self.db.get_chat_messages(chat_id)

        # Format messages for display with HTML
        history_html = ""
        for msg in messages:
            if msg.role is MessageRole.USER:
                content = msg.content.replace(chr(10), "<br>")
                history_html += (
                    f"<div style='margin-bottom: 1em;'><strong>👤 You:</strong><br>{content}</div>"
                )
            elif msg.role is MessageRole.ASSISTANT:
                # Render markdown for assistant
                from markdown import markdown

                rendered = markdown(msg.content)
                history_html += (
                    f"<div style='margin-bottom: 1em;'>"
                    f"<strong>🤖 Assistant:</strong><br>{rendered}</div>"
                )

        self.chat_history.set_content(history_html)

    async def rename_chat(self) -> None:
        """Rename selected chat."""
        if not self.current_chat_id:
            ui.notify("No chat selected!", type="warning")
            return

        chat = self.db.get_chat(self.current_chat_id)
        if not chat:
            return

        # Use dialog for input
        with ui.dialog() as dialog, ui.card():
            ui.markdown("### Rename Chat")
            new_name_input = ui.input(label="New name", value=chat.name).classes("w-96")

            async def confirm_rename() -> None:
                if new_name_input.value.strip():
                    try:
                        if self.current_chat_id is not None:
                            self.db.update_chat_name(
                                self.current_chat_id, new_name_input.value.strip()
                            )
                            await self.refresh_chat_list(self.current_chat_id)
                        self.status_label.set_text("Chat renamed").style("color: green")
                        logger.info(f"Renamed chat {self.current_chat_id}")
                        dialog.close()
                    except Exception as e:
                        logger.error(f"Failed to rename chat: {e}")
                        ui.notify(f"Error: {str(e)}", type="negative")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Rename", on_click=confirm_rename).props("color=primary")

        dialog.open()

    async def delete_chat(self) -> None:
        """Delete selected chat."""
        if not self.current_chat_id:
            ui.notify("No chat selected!", type="warning")
            return

        chat = self.db.get_chat(self.current_chat_id)
        if not chat:
            return

        # Confirmation dialog
        with ui.dialog() as dialog, ui.card():
            ui.markdown("### Confirm Delete")
            ui.label(f"Delete chat '{chat.name}'?")
            ui.label("This will delete all messages.")

            async def confirm_delete() -> None:
                try:
                    if self.current_chat_id is not None:
                        self.db.delete_chat(self.current_chat_id)
                    self.current_chat_id = None
                    await self.refresh_chat_list()
                    self.chat_history.set_content("")
                    self.chat_input.value = ""
                    self.status_label.set_text("Chat deleted").style("color: green")
                    dialog.close()
                except Exception as e:
                    logger.error(f"Failed to delete chat: {e}")
                    ui.notify(f"Error: {str(e)}", type="negative")

            with ui.row():
                ui.button("Cancel", on_click=dialog.close)
                ui.button("Delete", on_click=confirm_delete).props("color=negative")

        dialog.open()

    async def upload_file(self) -> None:
        """Handle file upload."""

        async def handle_upload(e: events.UploadEventArguments) -> None:
            try:
                file_path = e.file.name
                file_content = await e.file.read()

                path = Path(file_path)
                extension = path.suffix.lower()
                filename = path.name

                # Check file type
                if extension in FileExtension.image_extensions():
                    # Handle image
                    formatted = format_image_content(filename)
                    self.chat_input.value += formatted
                    self.status_label.set_text(f"Image '{filename}' loaded").style("color: green")
                    logger.info(f"Uploaded image: {filename}")
                elif extension in FileExtension.text_extensions():
                    # Handle text file
                    content_str = file_content.decode("utf-8")
                    formatted = format_file_content(filename, content_str)
                    self.chat_input.value += formatted
                    self.status_label.set_text(f"File '{filename}' loaded").style("color: green")
                    logger.info(f"Uploaded file: {filename}")
                else:
                    ui.notify(f"Unsupported file type: {extension}", type="warning")
            except Exception as e:
                logger.error(f"Failed to upload file: {e}")
                ui.notify(f"Error: {str(e)}", type="negative")

        ui.upload(on_upload=handle_upload, auto_upload=True).classes("hidden").run_method(
            "pickFiles"
        )

    async def send_message(self) -> None:
        """Send message to OpenAI."""
        if not self.current_chat_id:
            ui.notify("Please select or create a chat first!", type="warning")
            return

        user_message = self.chat_input.value.strip()
        if not user_message:
            ui.notify("Please enter a message!", type="warning")
            return

        settings = self.db.get_settings()
        if not settings.openai_api_key:
            ui.notify("Please configure your OpenAI API key in Settings!", type="warning")
            return

        try:
            # Check if first message
            messages = self.db.get_chat_messages(self.current_chat_id)
            is_first_message = len([m for m in messages if m.role == MessageRole.USER.value]) == 0

            # Add user message
            self.db.add_message(self.current_chat_id, MessageRole.USER.value, user_message)

            # Auto-rename chat
            if is_first_message:
                chat_name = truncate_text(user_message, 40)
                self.db.update_chat_name(self.current_chat_id, chat_name)
                await self.refresh_chat_list(self.current_chat_id)

            # Reload messages
            await self.load_chat_messages(self.current_chat_id)

            # Clear input
            self.chat_input.value = ""

            # Prepare for streaming
            messages = self.db.get_chat_messages(self.current_chat_id)
            message_list = [
                (str(msg.role), msg.content) for msg in messages if str(msg.role) != "system"
            ]
            formatted_messages = format_chat_messages_for_openai(message_list)

            # Setup streaming
            self.streaming_client = StreamingClient(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
            self.stream_queue = StreamQueue()

            # Add assistant header
            current_html = self.chat_history.content
            self.chat_history.set_content(
                current_html + "<div style='margin-bottom: 1em;'><strong>🤖 Assistant:</strong><br>"
            )

            full_response = ""

            def on_token(token: str) -> None:
                nonlocal full_response
                full_response += token
                if self.stream_queue:
                    self.stream_queue.add_token(token)

            def on_complete(response: str) -> None:
                if self.current_chat_id is not None:
                    self.db.add_message(
                        self.current_chat_id, MessageRole.ASSISTANT.value, full_response
                    )
                if self.stream_queue:
                    self.stream_queue.mark_complete()
                logger.info("Message sent and response received")

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
            self.send_button.set_enabled(False)
            self.stop_button.set_enabled(True)
            self.status_label.set_text("Streaming...").style("color: blue")

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            ui.notify(f"Error: {str(e)}", type="negative")
            self.status_label.set_text("Error").style("color: red")

    async def stop_streaming(self) -> None:
        """Stop the streaming."""
        if self.streaming_client:
            self.streaming_client.stop_streaming()
            self.is_streaming = False
            self.send_button.set_enabled(True)
            self.stop_button.set_enabled(False)
            self.status_label.set_text("Stopped").style("color: orange")
            logger.info("Streaming stopped by user")
