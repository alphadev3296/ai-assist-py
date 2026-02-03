# Upgrade Notes - AI Assistant Application

## Overview

This document summarizes the major architectural upgrade from raw SQLite3 to SQLAlchemy ORM with Pydantic validation and type-safe enumerations.

## Major Changes

### 1. SQLAlchemy ORM Migration

**Before:** Direct SQLite3 queries with manual SQL strings
**After:** SQLAlchemy 2.0+ ORM with declarative models and session management

**New Files:**

- `app/orm_models.py` - SQLAlchemy declarative models (Base, ChatModel, MessageModel, etc.)

**Modified Files:**

- `app/db.py` - Complete rewrite using SQLAlchemy ORM
  - Uses `sessionmaker` and context managers (`with self.SessionLocal()`)
  - Proper relationship management with cascade deletes
  - Comprehensive docstrings with Args, Returns, Raises sections
  - All CRUD operations migrated: create_chat, get_all_chats, add_message, etc.

**Benefits:**

- Eliminates SQL injection risks
- Automatic relationship management
- Type-safe database operations
- Better error handling with proper transaction rollback

### 2. Pydantic Models with Validation

**Before:** Dataclasses with no validation
**After:** Pydantic BaseModel with field validators

**Modified Files:**

- `app/models.py` - Converted all dataclasses to Pydantic models
  - `Settings` model has `@field_validator` for API key and model validation
  - Proper type hints with Python 3.12 syntax (X | None)

**Benefits:**

- Runtime data validation
- Automatic type coercion
- Better error messages for invalid data

### 3. Type-Safe Enumerations

**Before:** String literals like "user", "assistant", "system"
**After:** Enumerations with helper methods

**New Files:**

- `app/enums.py` - Central enum definitions
  - `MessageRole` - SYSTEM, USER, ASSISTANT
  - `FileExtension` - Text and image file types with helper methods
  - `OpenAIModel` - All supported OpenAI models

**Modified Files:**

- `app/ui/chat_tab.py` - Uses `MessageRole.USER.value`, `MessageRole.ASSISTANT.value`
- `app/ui/settings_tab.py` - Uses `OpenAIModel.get_all_values()`
- `app/utils.py` - Uses enums throughout

**Benefits:**

- IDE autocomplete support
- Prevents typos
- Centralized model/role definitions
- Helper methods like `FileExtension.all_extensions()`

### 4. Image Upload Support

**New Features:**

- Support for .png, .jpg, .jpeg, .gif, .webp files
- Base64 encoding for image data
- Size limits: 10MB for images, 1MB for text files
- Automatic MIME type detection

**Modified Files:**

- `app/utils.py` - Added `read_image_file()`, `get_image_mime_type()`, `format_image_content()`
- `app/ui/chat_tab.py` - Enhanced file upload handler with image support
  - Branching logic: if image → read_image_file(), if text → read_text_file()
  - Different error messages based on file type

**Database Changes:**

- `MessageModel.image_data` field stores base64 encoded images

### 5. Keyboard Shortcuts

**New Features:**

- Ctrl+Enter to send messages in chat tab

**Modified Files:**

- `app/ui/chat_tab.py`
  - Input field has `return_keyboard_events=True`
  - Event handler detects Ctrl+Enter patterns: `"+Return:36"` or `"Control_L:37\r"`

**Note:** FreeSimpleGUI has limited Ctrl+Enter detection - may not work in all cases

### 6. Enhanced Documentation

**All Files Updated:**

- PEP-257 compliant docstrings
- Google-style docstring format (Args, Returns, Raises)
- Module-level docstrings with detailed descriptions
- Class docstrings explaining purpose and responsibilities

**Modified Files:**

- `app/ui/chat_tab.py` - Enhanced function docstrings
- `app/ui/preset_tab.py` - Enhanced function and class docstrings
- `app/ui/settings_tab.py` - Enhanced docstrings
- `app/db.py` - Comprehensive docstrings for all methods

## Dependencies Updated

**New Requirements:**

- `sqlalchemy>=2.0.25` - ORM layer
- `pydantic>=2.8.0` - Data validation

**Updated Files:**

- `requirements.txt` - Added SQLAlchemy and Pydantic
- `pyproject.toml` - Added dependencies to project config

## Code Quality Improvements

### Type Hints

- All functions have proper type hints
- Uses Python 3.12 syntax: `X | None` instead of `Optional[X]`
- Uses built-in collection types: `list`, `dict`, `tuple`

### Formatting

- F-strings throughout
- Line length limit: 100 characters (configured in pyproject.toml)
- Ruff linter compliant
- Mypy type checker compliant

### Logging

- All logging uses loguru
- Log files rotate in `logs/` directory
- Proper log levels (DEBUG, INFO, ERROR)

### Error Handling

- Try-except blocks with specific exceptions
- Database transactions with proper rollback
- User-friendly error popups
- Detailed error logging

## Migration Guide

### For Users

1. Delete old `data.db` file (incompatible schema)
2. Install new dependencies: `pip install -e .`
3. Run application: `python -m app`
4. Reconfigure API key in Settings tab

### For Developers

1. Install dev dependencies: `pip install -e ".[dev]"`
2. Run linter: `python lint.py` or `lint.bat`
3. Run type checker: `mypy app/`
4. Build executable: `python build.py`

## Testing Checklist

- [x] All files pass ruff linting
- [x] All files pass mypy type checking
- [x] Chat creation and message sending
- [x] Text file upload (.txt, .md, .py, .json)
- [x] Image file upload (.png, .jpg, .jpeg, .gif, .webp)
- [x] Ctrl+Enter keyboard shortcut
- [x] Preset creation and execution
- [x] Settings persistence
- [x] Chat history loading
- [ ] Multi-chat switching
- [ ] Chat renaming/deletion
- [ ] Preset field management
- [ ] Response streaming
- [ ] Error handling for invalid API keys

## Known Issues

1. **Ctrl+Enter Detection**: FreeSimpleGUI has limited support for Ctrl+Enter. The current implementation may not work consistently across all systems.

2. **Image Display**: Images are stored as base64 but not displayed in the UI - only a placeholder text is shown.

3. **Database Migration**: No automatic migration from old SQLite schema. Users must delete old database file.

## Future Improvements

1. Add database migration tool (Alembic)
2. Implement image preview in chat history
3. Add more keyboard shortcuts (Ctrl+N for new chat, etc.)
4. Add unit tests for database operations
5. Add integration tests for UI components
6. Implement dark mode theme
7. Add export chat history feature
8. Add search functionality across chats

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.
