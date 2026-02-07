"""SQLAlchemy ORM models for the AI Assistant application."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base class for all ORM models."""

    pass


class ChatModel(Base):
    """Chat conversation ORM model."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel", back_populates="chat", cascade="all, delete-orphan"
    )


class MessageModel(Base):
    """Message ORM model."""

    __tablename__ = "messages"
    __table_args__ = ({"sqlite_autoincrement": True},)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(Integer, ForeignKey("chats.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    chat: Mapped["ChatModel"] = relationship("ChatModel", back_populates="messages")


class PresetModel(Base):
    """Preset template ORM model."""

    __tablename__ = "presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())

    fields: Mapped[list["PresetFieldModel"]] = relationship(
        "PresetFieldModel", back_populates="preset", cascade="all, delete-orphan"
    )
    runs: Mapped[list["PresetRunModel"]] = relationship(
        "PresetRunModel", back_populates="preset", cascade="all, delete-orphan"
    )


class PresetFieldModel(Base):
    """Preset field ORM model."""

    __tablename__ = "preset_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preset_id: Mapped[int] = mapped_column(Integer, ForeignKey("presets.id"), nullable=False)
    field_name: Mapped[str] = mapped_column(String, nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False, default="")

    preset: Mapped["PresetModel"] = relationship("PresetModel", back_populates="fields")


class PresetRunModel(Base):
    """Preset run ORM model."""

    __tablename__ = "preset_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    preset_id: Mapped[int] = mapped_column(Integer, ForeignKey("presets.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    response: Mapped[str] = mapped_column(Text, nullable=False)

    preset: Mapped["PresetModel"] = relationship("PresetModel", back_populates="runs")


class SettingsModel(Base):
    """Settings ORM model."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
