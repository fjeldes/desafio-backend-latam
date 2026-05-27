"""
SQLAlchemy ORM models – database table definitions.

Defines the ``users`` table and the Role enumeration used for the
``role`` column. All timestamps are stored with UTC timezone awareness.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime, Enum, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


class Role(str, PyEnum):
    """
    Allowed user role values.

    Values
    ------
    ADMIN : "admin"
        Full system access.
    USER  : "user"
        Standard access (default).
    GUEST : "guest"
        Read-only or restricted access.
    """

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(Base):
    """
    Represents a user record in the ``users`` table.

    Columns
    -------
    id : UUID
        Primary key, auto-generated via uuid4.
    username : str (50, unique, indexed)
        Unique username composed of alphanumeric characters and underscores.
    email : str (255, unique, indexed)
        Unique, validated email address.
    first_name : str (100)
        User's given name.
    last_name : str (100)
        User's family name.
    role : Role
        One of ``admin``, ``user``, or ``guest`` (default: ``user``).
    active : bool
        Whether the user account is active (default: True).
    created_at : datetime (tz-aware)
        Automatically set to current UTC time on creation.
    updated_at : datetime (tz-aware)
        Automatically set to current UTC time on creation and updated on every change.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role", create_constraint=True),
        nullable=False,
        default=Role.USER,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
