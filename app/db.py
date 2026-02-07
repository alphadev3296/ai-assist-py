"""Database operations for the AI Assistant application using SQLAlchemy ORM."""

from datetime import datetime
from pathlib import Path
from typing import cast

from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.enums import MessageRole
from app.models import Chat, Message, Preset, PresetField, PresetRun, Settings
from app.orm_models import (
    Base,
    ChatModel,
    MessageModel,
    PresetFieldModel,
    PresetModel,
    PresetRunModel,
    SettingsModel,
)

DB_PATH = Path("ai_assistant.db")


class Database:
    """SQLite database manager using SQLAlchemy ORM."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._create_schema()
        logger.info(f"Connected to database at {self.db_path}")

    def _create_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create schema: {e}")
            raise

    # Settings operations
    def get_settings(self) -> Settings:
        """Get application settings.

        Returns:
            Settings object with API key and model configuration.
        """
        try:
            with self.SessionLocal() as session:
                api_key_row = session.execute(
                    select(SettingsModel).where(SettingsModel.key == "openai_api_key")
                ).scalar_one_or_none()
                model_row = session.execute(
                    select(SettingsModel).where(SettingsModel.key == "openai_model")
                ).scalar_one_or_none()

                return Settings(
                    openai_api_key=api_key_row.value if api_key_row else "",
                    openai_model=model_row.value if model_row else "gpt-4o-mini",
                )
        except Exception as e:
            logger.error(f"Failed to get settings: {e}")
            return Settings()

    def save_settings(self, settings: Settings) -> None:
        """Save application settings.

        Args:
            settings: Settings object to save.

        Raises:
            Exception: If settings cannot be saved.
        """
        try:
            with self.SessionLocal() as session:
                # Update or create API key
                api_key_setting = session.execute(
                    select(SettingsModel).where(SettingsModel.key == "openai_api_key")
                ).scalar_one_or_none()

                if api_key_setting:
                    api_key_setting.value = settings.openai_api_key
                else:
                    session.add(SettingsModel(key="openai_api_key", value=settings.openai_api_key))

                # Update or create model
                model_setting = session.execute(
                    select(SettingsModel).where(SettingsModel.key == "openai_model")
                ).scalar_one_or_none()

                if model_setting:
                    model_setting.value = settings.openai_model
                else:
                    session.add(SettingsModel(key="openai_model", value=settings.openai_model))

                session.commit()
                logger.info("Settings saved successfully")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise

    # Chat operations
    def create_chat(self, name: str) -> int:
        """Create a new chat and return its ID.

        Args:
            name: Name of the chat.

        Returns:
            ID of the created chat.

        Raises:
            Exception: If chat cannot be created.
        """
        try:
            with self.SessionLocal() as session:
                chat = ChatModel(name=name, created_at=datetime.now())
                session.add(chat)
                session.commit()
                session.refresh(chat)
                logger.info(f"Created chat {chat.id}: {name}")
                return cast(int, chat.id)
        except Exception as e:
            logger.error(f"Failed to create chat: {e}")
            raise

    def get_all_chats(self) -> list[Chat]:
        """Get all chats ordered by creation date.

        Returns:
            List of Chat objects.
        """
        try:
            with self.SessionLocal() as session:
                chat_models = (
                    session.execute(select(ChatModel).order_by(ChatModel.created_at.desc()))
                    .scalars()
                    .all()
                )
                return [Chat(id=c.id, name=c.name, created_at=c.created_at) for c in chat_models]
        except Exception as e:
            logger.error(f"Failed to get chats: {e}")
            return []

    def get_chat(self, chat_id: int) -> Chat | None:
        """Get a specific chat by ID.

        Args:
            chat_id: ID of the chat.

        Returns:
            Chat object or None if not found.
        """
        try:
            with self.SessionLocal() as session:
                chat_model = session.execute(
                    select(ChatModel).where(ChatModel.id == chat_id)
                ).scalar_one_or_none()
                if chat_model:
                    return Chat(
                        id=chat_model.id,
                        name=chat_model.name,
                        created_at=chat_model.created_at,
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get chat: {e}")
            return None

    def update_chat_name(self, chat_id: int, name: str) -> None:
        """Update chat name.

        Args:
            chat_id: ID of the chat.
            name: New name for the chat.

        Raises:
            Exception: If chat name cannot be updated.
        """
        try:
            with self.SessionLocal() as session:
                chat = session.execute(
                    select(ChatModel).where(ChatModel.id == chat_id)
                ).scalar_one_or_none()
                if chat:
                    chat.name = name
                    session.commit()
                    logger.info(f"Updated chat {chat_id} name to: {name}")
        except Exception as e:
            logger.error(f"Failed to update chat name: {e}")
            raise

    def delete_chat(self, chat_id: int) -> None:
        """Delete a chat and all its messages.

        Args:
            chat_id: ID of the chat.

        Raises:
            Exception: If chat cannot be deleted.
        """
        try:
            with self.SessionLocal() as session:
                chat = session.execute(
                    select(ChatModel).where(ChatModel.id == chat_id)
                ).scalar_one_or_none()
                if chat:
                    session.delete(chat)
                    session.commit()
                    logger.info(f"Deleted chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to delete chat: {e}")
            raise

    # Message operations
    def add_message(self, chat_id: int, role: str, content: str) -> int:
        """Add a message to a chat and return its ID.

        Args:
            chat_id: ID of the chat.
            role: Role of the message sender (system, user, assistant).
            content: Content of the message.

        Returns:
            ID of the created message.

        Raises:
            Exception: If message cannot be added.
        """
        try:
            with self.SessionLocal() as session:
                message = MessageModel(
                    chat_id=chat_id, role=role, content=content, created_at=datetime.now()
                )
                session.add(message)
                session.commit()
                session.refresh(message)
                logger.debug(f"Added message {message.id} to chat {chat_id}")
                return cast(int, message.id)
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise

    def get_chat_messages(self, chat_id: int) -> list[Message]:
        """Get all messages for a chat ordered by creation date.

        Args:
            chat_id: ID of the chat.

        Returns:
            List of Message objects.
        """
        try:
            with self.SessionLocal() as session:
                message_models = (
                    session.execute(
                        select(MessageModel)
                        .where(MessageModel.chat_id == chat_id)
                        .order_by(MessageModel.created_at.asc())
                    )
                    .scalars()
                    .all()
                )
                return [
                    Message(
                        id=m.id,
                        chat_id=m.chat_id,
                        role=MessageRole(m.role),
                        content=m.content,
                        created_at=m.created_at,
                    )
                    for m in message_models
                ]
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []

    # Preset operations
    def create_preset(self, name: str, system_prompt: str = "") -> int:
        """Create a new preset and return its ID.

        Args:
            name: Name of the preset.
            system_prompt: System prompt for the preset (default: empty).

        Returns:
            ID of the created preset.

        Raises:
            Exception: If preset cannot be created.
        """
        try:
            with self.SessionLocal() as session:
                preset = PresetModel(
                    name=name, system_prompt=system_prompt, created_at=datetime.now()
                )
                session.add(preset)
                session.commit()
                session.refresh(preset)
                logger.info(f"Created preset {preset.id}: {name}")
                return cast(int, preset.id)
        except Exception as e:
            logger.error(f"Failed to create preset: {e}")
            raise

    def get_all_presets(self) -> list[Preset]:
        """Get all presets ordered by creation date.

        Returns:
            List of Preset objects.
        """
        try:
            with self.SessionLocal() as session:
                preset_models = (
                    session.execute(select(PresetModel).order_by(PresetModel.created_at.asc()))
                    .scalars()
                    .all()
                )
                return [
                    Preset(
                        id=p.id, name=p.name, system_prompt=p.system_prompt, created_at=p.created_at
                    )
                    for p in preset_models
                ]
        except Exception as e:
            logger.error(f"Failed to get presets: {e}")
            return []

    def get_preset(self, preset_id: int) -> Preset | None:
        """Get a specific preset by ID.

        Args:
            preset_id: ID of the preset.

        Returns:
            Preset object or None if not found.
        """
        try:
            with self.SessionLocal() as session:
                preset_model = session.execute(
                    select(PresetModel).where(PresetModel.id == preset_id)
                ).scalar_one_or_none()
                if preset_model:
                    return Preset(
                        id=preset_model.id,
                        name=preset_model.name,
                        system_prompt=preset_model.system_prompt,
                        created_at=preset_model.created_at,
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get preset: {e}")
            return None

    def update_preset(self, preset_id: int, name: str, system_prompt: str) -> None:
        """Update preset name and system prompt.

        Args:
            preset_id: ID of the preset.
            name: New name for the preset.
            system_prompt: New system prompt.

        Raises:
            Exception: If preset cannot be updated.
        """
        try:
            with self.SessionLocal() as session:
                preset = session.execute(
                    select(PresetModel).where(PresetModel.id == preset_id)
                ).scalar_one_or_none()
                if preset:
                    preset.name = name
                    preset.system_prompt = system_prompt
                    session.commit()
                    logger.info(f"Updated preset {preset_id}")
        except Exception as e:
            logger.error(f"Failed to update preset: {e}")
            raise

    def delete_preset(self, preset_id: int) -> None:
        """Delete a preset and all its fields and runs.

        Args:
            preset_id: ID of the preset.

        Raises:
            Exception: If preset cannot be deleted.
        """
        try:
            with self.SessionLocal() as session:
                preset = session.execute(
                    select(PresetModel).where(PresetModel.id == preset_id)
                ).scalar_one_or_none()
                if preset:
                    session.delete(preset)
                    session.commit()
                    logger.info(f"Deleted preset {preset_id}")
        except Exception as e:
            logger.error(f"Failed to delete preset: {e}")
            raise

    # Preset field operations
    def add_preset_field(self, preset_id: int, field_name: str, field_value: str = "") -> int:
        """Add a field to a preset and return its ID.

        Args:
            preset_id: ID of the preset.
            field_name: Name of the field.
            field_value: Value of the field (default: empty).

        Returns:
            ID of the created field.

        Raises:
            Exception: If field cannot be added.
        """
        try:
            with self.SessionLocal() as session:
                field = PresetFieldModel(
                    preset_id=preset_id, field_name=field_name, field_value=field_value
                )
                session.add(field)
                session.commit()
                session.refresh(field)
                logger.debug(f"Added field {field.id} to preset {preset_id}")
                return cast(int, field.id)
        except Exception as e:
            logger.error(f"Failed to add preset field: {e}")
            raise

    def get_preset_fields(self, preset_id: int) -> list[PresetField]:
        """Get all fields for a preset.

        Args:
            preset_id: ID of the preset.

        Returns:
            List of PresetField objects.
        """
        try:
            with self.SessionLocal() as session:
                field_models = (
                    session.execute(
                        select(PresetFieldModel)
                        .where(PresetFieldModel.preset_id == preset_id)
                        .order_by(PresetFieldModel.id.asc())
                    )
                    .scalars()
                    .all()
                )
                return [
                    PresetField(
                        id=f.id,
                        preset_id=f.preset_id,
                        field_name=f.field_name,
                        field_value=f.field_value,
                    )
                    for f in field_models
                ]
        except Exception as e:
            logger.error(f"Failed to get preset fields: {e}")
            return []

    def get_preset_field(self, field_id: int) -> PresetField | None:
        """Get a single preset field by ID.

        Args:
            field_id: ID of the field.

        Returns:
            PresetField object or None if not found.
        """
        try:
            with self.SessionLocal() as session:
                field = session.execute(
                    select(PresetFieldModel).where(PresetFieldModel.id == field_id)
                ).scalar_one_or_none()
                if field:
                    return PresetField(
                        id=field.id,
                        preset_id=field.preset_id,
                        field_name=field.field_name,
                        field_value=field.field_value,
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get preset field: {e}")
            return None

    def update_preset_field(self, field_id: int, field_name: str, field_value: str) -> None:
        """Update a preset field.

        Args:
            field_id: ID of the field.
            field_name: New field name.
            field_value: New field value.

        Raises:
            Exception: If field cannot be updated.
        """
        try:
            with self.SessionLocal() as session:
                field = session.execute(
                    select(PresetFieldModel).where(PresetFieldModel.id == field_id)
                ).scalar_one_or_none()
                if field:
                    field.field_name = field_name
                    field.field_value = field_value
                    session.commit()
                    logger.debug(f"Updated field {field_id}")
        except Exception as e:
            logger.error(f"Failed to update preset field: {e}")
            raise

    def delete_preset_field(self, field_id: int) -> None:
        """Delete a preset field.

        Args:
            field_id: ID of the field.

        Raises:
            Exception: If field cannot be deleted.
        """
        try:
            with self.SessionLocal() as session:
                field = session.execute(
                    select(PresetFieldModel).where(PresetFieldModel.id == field_id)
                ).scalar_one_or_none()
                if field:
                    session.delete(field)
                    session.commit()
                    logger.debug(f"Deleted field {field_id}")
        except Exception as e:
            logger.error(f"Failed to delete preset field: {e}")
            raise

    def clear_preset_field_values(self, preset_id: int) -> None:
        """Clear all field values for a preset.

        Args:
            preset_id: ID of the preset.

        Raises:
            Exception: If field values cannot be cleared.
        """
        try:
            with self.SessionLocal() as session:
                fields = (
                    session.execute(
                        select(PresetFieldModel).where(PresetFieldModel.preset_id == preset_id)
                    )
                    .scalars()
                    .all()
                )
                for field in fields:
                    field.field_value = ""
                session.commit()
                logger.info(f"Cleared field values for preset {preset_id}")
        except Exception as e:
            logger.error(f"Failed to clear preset field values: {e}")
            raise

    # Preset run operations
    def add_preset_run(self, preset_id: int, response: str) -> int:
        """Add a preset run and return its ID.

        Args:
            preset_id: ID of the preset.
            response: Response text from the run.

        Returns:
            ID of the created run.

        Raises:
            Exception: If run cannot be added.
        """
        try:
            with self.SessionLocal() as session:
                run = PresetRunModel(
                    preset_id=preset_id, created_at=datetime.now(), response=response
                )
                session.add(run)
                session.commit()
                session.refresh(run)
                logger.info(f"Added run {run.id} for preset {preset_id}")
                return cast(int, run.id)
        except Exception as e:
            logger.error(f"Failed to add preset run: {e}")
            raise

    def get_preset_runs(self, preset_id: int) -> list[PresetRun]:
        """Get all runs for a preset ordered by creation date.

        Args:
            preset_id: ID of the preset.

        Returns:
            List of PresetRun objects.
        """
        try:
            with self.SessionLocal() as session:
                run_models = (
                    session.execute(
                        select(PresetRunModel)
                        .where(PresetRunModel.preset_id == preset_id)
                        .order_by(PresetRunModel.created_at.asc())
                    )
                    .scalars()
                    .all()
                )
                return [
                    PresetRun(
                        id=r.id,
                        preset_id=r.preset_id,
                        created_at=r.created_at,
                        response=r.response,
                    )
                    for r in run_models
                ]
        except Exception as e:
            logger.error(f"Failed to get preset runs: {e}")
            return []

    def close(self) -> None:
        """Close database connection.

        Note: With SQLAlchemy, the session pool is managed automatically,
        but we can dispose of the engine.
        """
        try:
            self.engine.dispose()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Failed to close database: {e}")
