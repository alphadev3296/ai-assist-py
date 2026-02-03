"""Chat tab UI for the AI Assistant application."""

from typing import Any

import FreeSimpleGUI as sg  # type: ignore
from loguru import logger

from app.db import Database
from app.enums import FileExtension, MessageRole
from app.openai_client import StreamingClient, StreamQueue
from app.utils import (
    format_chat_messages_for_openai,
    format_file_content,
    format_image_content,
    read_image_file,
    read_text_file,
    truncate_text,
)


class ChatTabState:
    """State manager for chat tab."""

    def __init__(self, db: Database) -> None:
        """Initialize chat tab state.

        Args:
            db: Database instance.
        """
        self.db = db
        self.current_chat_id: int | None = None
        self.streaming_client: StreamingClient | None = None
        self.stream_queue: StreamQueue | None = None
        self.is_streaming = False


def create_chat_tab(db: Database) -> list[list[sg.Element]]:
    """Create the chat tab layout.

    Args:
        db: Database instance.

    Returns:
        Layout for chat tab.
    """
    # Load existing chats
    chats = db.get_all_chats()
    chat_names = [f"{chat.id}: {chat.name}" for chat in chats]

    # Left panel - chat list
    left_panel = [
        [sg.Text("Chats", font=("Arial", 12, "bold"))],
        [
            sg.Listbox(
                values=chat_names,
                size=(30, 20),
                key="-CHAT-LIST-",
                enable_events=True,
                right_click_menu=["&Right", ["Rename Chat", "Delete Chat"]],
                expand_y=True,
            )
        ],
        [sg.Button("New Chat", key="-CHAT-NEW-", size=(28, 1))],
    ]

    # Right panel - messages and input
    right_panel = [
        [sg.Text("Message History", font=("Arial", 12, "bold"))],
        [
            sg.Multiline(
                size=(80, 20),
                key="-CHAT-HISTORY-",
                disabled=True,
                autoscroll=True,
                write_only=False,
                expand_x=True,
                expand_y=True,
            )
        ],
        [sg.Text("Your Message:")],
        [
            sg.Multiline(
                size=(80, 5),
                key="-CHAT-INPUT-",
                enable_events=True,
                return_keyboard_events=True,
                expand_x=True,
            )
        ],
        [
            sg.Button("Upload File", key="-CHAT-UPLOAD-"),
            sg.Button("Send", key="-CHAT-SEND-"),
            sg.Button("Stop", key="-CHAT-STOP-", disabled=True),
            sg.Text("", key="-CHAT-STATUS-", size=(40, 1)),
            sg.Text("(Ctrl+Enter to send)", font=("Arial", 8), text_color="gray"),
        ],
    ]

    layout = [
        [
            sg.Column(left_panel, vertical_alignment="top", expand_y=True),
            sg.VerticalSeparator(),
            sg.Column(right_panel, vertical_alignment="top", expand_x=True, expand_y=True),
        ]
    ]

    return layout


def refresh_chat_list(window: sg.Window, db: Database, selected_chat_id: int | None = None) -> None:
    """
    Refresh the chat list in the UI.

    Args:
        window: Main window
        db: Database instance
        selected_chat_id: ID of chat to select after refresh
    """
    chats = db.get_all_chats()
    chat_names = [f"{chat.id}: {chat.name}" for chat in chats]
    window["-CHAT-LIST-"].update(values=chat_names)

    # Reselect chat if specified
    if selected_chat_id:
        for i, chat in enumerate(chats):
            if chat.id == selected_chat_id:
                window["-CHAT-LIST-"].update(set_to_index=[i])
                break


def load_chat_messages(window: sg.Window, db: Database, chat_id: int) -> None:
    """
    Load and display messages for a chat.

    Args:
        window: Main window
        db: Database instance
        chat_id: Chat ID to load
    """
    messages = db.get_chat_messages(chat_id)

    # Format messages for display
    history_text = ""
    for msg in messages:
        if msg.role is MessageRole.USER:
            history_text += f"👤 You:\n{msg.content}\n\n"
        elif msg.role is MessageRole.ASSISTANT:
            history_text += f"🤖 Assistant:\n{msg.content}\n\n"

    window["-CHAT-HISTORY-"].update(history_text)


def handle_chat_events(
    event: str,
    values: dict[str, Any],
    window: sg.Window,
    state: ChatTabState,
) -> None:
    """Handle events in the chat tab.

    Args:
        event: Event string.
        values: Values dictionary.
        window: Main window.
        state: Chat tab state.
    """
    # Check for Ctrl+Enter in input field
    if event == "-CHAT-INPUT-" and values["-CHAT-INPUT-"]:
        # Check if Ctrl+Enter was pressed
        if "\r\n" in values["-CHAT-INPUT-"] or "\n" in values["-CHAT-INPUT-"]:
            # This is a normal newline, not Ctrl+Enter
            pass
        # Note: FreeSimpleGUI doesn't directly expose Ctrl+Enter, but we can check for Return key
        # Users can use the Send button or we can add a custom key binding

    # Handle Ctrl+Enter via special key event
    if event.endswith("+Return:36") or event == "Control_L:37\r":
        # Trigger send action
        event = "-CHAT-SEND-"

    # Check for streaming updates
    if state.is_streaming and state.stream_queue:
        token = state.stream_queue.get_token()
        if token is not None:
            # Append token to history
            current = window["-CHAT-HISTORY-"].get()
            window["-CHAT-HISTORY-"].update(current + token)
        elif state.stream_queue.is_complete():
            # Streaming complete
            state.is_streaming = False
            window["-CHAT-SEND-"].update(disabled=False)
            window["-CHAT-STOP-"].update(disabled=True)
            window["-CHAT-STATUS-"].update("", text_color="black")
        elif state.stream_queue.has_error():
            # Streaming error
            error = state.stream_queue.get_error()
            state.is_streaming = False
            window["-CHAT-SEND-"].update(disabled=False)
            window["-CHAT-STOP-"].update(disabled=True)
            window["-CHAT-STATUS-"].update("Error occurred", text_color="red")
            sg.popup_error(f"Error during streaming:\n{str(error)}", title="Error")

    if event == "-CHAT-NEW-":
        # Create new chat
        try:
            chat_id = state.db.create_chat("New Chat")
            refresh_chat_list(window, state.db, chat_id)
            state.current_chat_id = chat_id
            window["-CHAT-HISTORY-"].update("")
            window["-CHAT-INPUT-"].update("")
            window["-CHAT-STATUS-"].update("New chat created", text_color="green")
            logger.info(f"Created new chat: {chat_id}")
        except Exception as e:
            logger.error(f"Failed to create chat: {e}")
            sg.popup_error(f"Failed to create chat:\n{str(e)}", title="Error")

    elif event == "-CHAT-LIST-":
        # Chat selected from list
        if values["-CHAT-LIST-"]:
            selected = values["-CHAT-LIST-"][0]
            # Extract chat ID from "ID: Name" format
            chat_id = int(selected.split(":")[0])
            state.current_chat_id = chat_id
            load_chat_messages(window, state.db, chat_id)
            window["-CHAT-STATUS-"].update("")
            logger.info(f"Loaded chat: {chat_id}")

    elif event == "Rename Chat":
        # Rename selected chat
        if not state.current_chat_id:
            sg.popup_error("No chat selected!", title="Error")
            return

        chat = state.db.get_chat(state.current_chat_id)
        if not chat:
            return

        new_name = sg.popup_get_text(
            "Enter new chat name:",
            title="Rename Chat",
            default_text=chat.name,
        )

        if new_name and new_name.strip():
            try:
                state.db.update_chat_name(state.current_chat_id, new_name.strip())
                refresh_chat_list(window, state.db, state.current_chat_id)
                window["-CHAT-STATUS-"].update("Chat renamed", text_color="green")
                logger.info(f"Renamed chat {state.current_chat_id} to: {new_name}")
            except Exception as e:
                logger.error(f"Failed to rename chat: {e}")
                sg.popup_error(f"Failed to rename chat:\n{str(e)}", title="Error")

    elif event == "Delete Chat":
        # Delete selected chat
        if not state.current_chat_id:
            sg.popup_error("No chat selected!", title="Error")
            return

        chat = state.db.get_chat(state.current_chat_id)
        if not chat:
            return

        response = sg.popup_yes_no(
            f"Are you sure you want to delete chat '{chat.name}'?\n\n"
            f"This will also delete all messages in this chat.",
            title="Confirm Delete",
            default_button="No",
        )

        if response == "Yes":
            try:
                state.db.delete_chat(state.current_chat_id)
                state.current_chat_id = None
                refresh_chat_list(window, state.db)
                window["-CHAT-HISTORY-"].update("")
                window["-CHAT-INPUT-"].update("")
                window["-CHAT-STATUS-"].update("Chat deleted", text_color="green")
                logger.info(f"Deleted chat {state.current_chat_id}")
            except Exception as e:
                logger.error(f"Failed to delete chat: {e}")
                sg.popup_error(f"Failed to delete chat:\n{str(e)}", title="Error")

    elif event == "-CHAT-UPLOAD-":
        # Upload file (text or image)
        file_path = sg.popup_get_file(
            "Select file to upload",
            title="Upload File",
            file_types=(
                ("All Supported", "*.txt *.md *.py *.json *.png *.jpg *.jpeg *.gif *.webp"),
                ("Text Files", "*.txt"),
                ("Markdown Files", "*.md"),
                ("Python Files", "*.py"),
                ("JSON Files", "*.json"),
                ("PNG Images", "*.png"),
                ("JPEG Images", "*.jpg *.jpeg"),
                ("GIF Images", "*.gif"),
                ("WebP Images", "*.webp"),
            ),
        )

        if file_path:
            from pathlib import Path

            path = Path(file_path)
            extension = path.suffix.lower()
            filename = path.name

            # Check if it's an image or text file
            if extension in FileExtension.image_extensions():
                # Handle image file
                image_data = read_image_file(file_path)
                if image_data:
                    formatted = format_image_content(filename)
                    current_input = window["-CHAT-INPUT-"].get()
                    window["-CHAT-INPUT-"].update(current_input + formatted)
                    window["-CHAT-STATUS-"].update(f"Image '{filename}' loaded", text_color="green")
                    logger.info(f"Uploaded image: {filename}")
                else:
                    sg.popup_error(
                        f"Failed to read image file.\n\n"
                        f"Allowed extensions: {', '.join(FileExtension.image_extensions())}\n"
                        f"Max size: 10MB",
                        title="Error",
                    )
            elif extension in FileExtension.text_extensions():
                # Handle text file
                content = read_text_file(file_path)
                if content:
                    formatted = format_file_content(filename, content)
                    current_input = window["-CHAT-INPUT-"].get()
                    window["-CHAT-INPUT-"].update(current_input + formatted)
                    window["-CHAT-STATUS-"].update(f"File '{filename}' loaded", text_color="green")
                    logger.info(f"Uploaded file: {filename}")
                else:
                    sg.popup_error(
                        f"Failed to read file.\n\n"
                        f"Allowed extensions: {', '.join(FileExtension.text_extensions())}\n"
                        f"Max size: 1MB",
                        title="Error",
                    )
            else:
                sg.popup_error(
                    f"Unsupported file type: {extension}\n\n"
                    f"Allowed: {', '.join(FileExtension.all_extensions())}",
                    title="Error",
                )

    elif event == "-CHAT-SEND-":
        # Send message
        if not state.current_chat_id:
            sg.popup_error("Please select or create a chat first!", title="Error")
            return

        user_message = values["-CHAT-INPUT-"].strip()
        if not user_message:
            sg.popup_error("Please enter a message!", title="Error")
            return

        # Get settings
        settings = state.db.get_settings()
        if not settings.openai_api_key:
            sg.popup_error("Please configure your OpenAI API key in Settings!", title="Error")
            return

        try:
            # Check if this is the first user message in a new chat
            messages = state.db.get_chat_messages(state.current_chat_id)
            is_first_message = len([m for m in messages if m.role == MessageRole.USER.value]) == 0

            # Add user message to database
            state.db.add_message(state.current_chat_id, MessageRole.USER.value, user_message)

            # Auto-rename chat if first message
            if is_first_message:
                chat_name = truncate_text(user_message, 40)
                state.db.update_chat_name(state.current_chat_id, chat_name)
                refresh_chat_list(window, state.db, state.current_chat_id)

            # Reload messages for display
            load_chat_messages(window, state.db, state.current_chat_id)

            # Clear input
            window["-CHAT-INPUT-"].update("")

            # Prepare messages for OpenAI
            messages = state.db.get_chat_messages(state.current_chat_id)
            message_list = [
                (str(msg.role), msg.content) for msg in messages if str(msg.role) != "system"
            ]
            formatted_messages = format_chat_messages_for_openai(message_list)

            # Setup streaming
            state.streaming_client = StreamingClient(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
            state.stream_queue = StreamQueue()

            # Add assistant message placeholder
            current = window["-CHAT-HISTORY-"].get()
            window["-CHAT-HISTORY-"].update(current + "\n🤖 Assistant:\n")

            full_response = ""

            def on_token(token: str) -> None:
                nonlocal full_response
                full_response += token
                if state.stream_queue:
                    state.stream_queue.add_token(token)

            def on_complete(response: str) -> None:
                # Save assistant message to database
                if state.current_chat_id is not None:
                    state.db.add_message(
                        state.current_chat_id, MessageRole.ASSISTANT.value, full_response
                    )
                if state.stream_queue:
                    state.stream_queue.mark_complete()
                logger.info("Message sent and response received")

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

            state.is_streaming = True
            window["-CHAT-SEND-"].update(disabled=True)
            window["-CHAT-STOP-"].update(disabled=False)
            window["-CHAT-STATUS-"].update("Streaming...", text_color="blue")

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            sg.popup_error(f"Failed to send message:\n{str(e)}", title="Error")
            window["-CHAT-STATUS-"].update("Error", text_color="red")

    elif event == "-CHAT-STOP-":
        # Stop streaming
        if state.streaming_client:
            state.streaming_client.stop_streaming()
            state.is_streaming = False
            window["-CHAT-SEND-"].update(disabled=False)
            window["-CHAT-STOP-"].update(disabled=True)
            window["-CHAT-STATUS-"].update("Stopped", text_color="orange")
            logger.info("Streaming stopped by user")
