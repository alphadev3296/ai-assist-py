# AI Assistant Desktop App

OpenAI-powered desktop assistant with multi-chat and preset tabs, built with Python 3.12 and FreeSimpleGUI.

## Features

- **Multi-Chat Interface**: Manage multiple conversations with chat history persistence
- **Preset Templates**: Create reusable prompt templates with custom fields
- **Streaming Responses**: Real-time token-by-token response streaming
- **File Upload**: Attach text files to your messages (.txt, .md, .py, .json)
- **Persistent Storage**: SQLite database for chats, messages, and presets
- **Configurable Settings**: Manage OpenAI API key and model selection

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
- Upload text files to include in messages
- Rename or delete chats via right-click menu
- Chat history persists across sessions

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
├── db.py                # Database operations
├── openai_client.py     # OpenAI API wrapper
├── models.py            # Data models
├── utils.py             # Utility functions
└── ui/                  # UI components
    ├── __init__.py
    ├── chat_tab.py      # Chat interface
    ├── settings_tab.py  # Settings interface
    └── preset_tab.py    # Preset interface
```

## License

MIT License. See `LICENSE` file for details.
