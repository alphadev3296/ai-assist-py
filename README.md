# AI Assistant Desktop App

OpenAI-powered desktop assistant with multi-chat and preset tabs, built with Python 3.12 and FreeSimpleGUI.

## Features

- **Multi-Chat Interface**: Manage multiple conversations with chat history persistence
- **Preset Templates**: Create reusable prompt templates with custom fields
- **Streaming Responses**: Real-time token-by-token response streaming
- **File Upload**: Attach text files (.txt, .md, .py, .json) and images (.png, .jpg, .jpeg, .gif, .webp) to messages
- **Image Support**: Upload images with automatic base64 encoding for vision models
- **Persistent Storage**: SQLAlchemy ORM with SQLite for chats, messages, and presets
- **Configurable Settings**: Manage OpenAI API key and model selection
- **Keyboard Shortcuts**: Use Ctrl+Enter to send messages in chat
- **Type Safety**: Pydantic models with field validation and enumerations

## Architecture

- **ORM Layer**: SQLAlchemy 2.0+ with declarative models and relationship management
- **Data Validation**: Pydantic models with field validators for API keys and settings
- **Type Safety**: Comprehensive type hints with Python 3.12 (X | None syntax)
- **Enumerations**: Type-safe enums for message roles, file extensions, and OpenAI models
- **Logging**: Structured logging with loguru, rotating log files in logs/ directory

## Requirements

- Python 3.12 or higher
- OpenAI API key

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -e .
```

For development tools (linting, type checking, build):

```bash
pip install -e ".[dev]"
```

## Running the Application

```bash
python -m app
```

## Configuration

On first run, navigate to the Settings tab to configure:

- **OpenAI API Key**: Your OpenAI API key
- **Model**: Select from available models (gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, etc.)

## Usage

### Chat Tab

- Create new chats with the "New Chat" button
- Send messages and receive streaming responses
- Upload text files (.txt, .md, .py, .json) up to 1MB
- Upload images (.png, .jpg, .jpeg, .gif, .webp) up to 10MB for vision models
- Use Ctrl+Enter keyboard shortcut to send messages
- Rename or delete chats via right-click menu
- Chat history persists across sessions with full message context

### Presets Tab

- Create preset templates with system prompts and custom fields
- Run presets multiple times with different field values
- View response history for each preset
- Edit, rename, or delete presets

## Development

### Linting

```bash
python lint.py
# or on Windows
lint.bat
```

### Type Checking

```bash
mypy app/
```

### Building Executable

```bash
python build.py
```

## Project Structure

```
app/
├── __main__.py          # Entry point
├── main.py              # GUI bootstrap
├── db.py                # Database operations (SQLAlchemy ORM)
├── orm_models.py        # SQLAlchemy declarative models
├── models.py            # Pydantic models with validation
├── enums.py             # Type-safe enumerations
├── openai_client.py     # OpenAI API wrapper
├── utils.py             # Utility functions (file handling, validation)
└── ui/                  # UI components
    ├── __init__.py
    ├── chat_tab.py      # Chat interface with image support
    ├── settings_tab.py  # Settings interface
    └── preset_tab.py    # Preset interface
```

## Database Schema

Built with SQLAlchemy ORM:

- **ChatModel**: Chat sessions with title and timestamps
- **MessageModel**: Individual messages with role, content, and image data
- **PresetModel**: Reusable templates with system prompts
- **PresetFieldModel**: Custom fields for presets (name, label, placeholder)
- **PresetRunModel**: History of preset executions with field values
- **SettingsModel**: Application settings (API key, model)

## License

MIT License. See `LICENSE` file for details.
