"""
Pydantic schemas for request/response validation and serialization.

Uses Pydantic v2 conventions with ``model_config`` for ORM mode and
``field_validator`` for custom validation logic.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RoleEnum(str, Enum):
    """
    Allowed user role values – mirrors the database Role enum.

    Values
    ------
    ADMIN : "admin"
    USER  : "user"   (default for new users)
    GUEST : "guest"
    """

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserBase(BaseModel):
    """
    Base schema shared by create and response models.

    Fields
    ------
    username : str (3-50 chars, alphanumeric + underscore only)
    email : EmailStr (max 255 chars)
    first_name : str (1-100 chars)
    last_name : str (1-100 chars)
    role : RoleEnum (default: user)
    active : bool (default: True)
    """

    username: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )
    email: EmailStr = Field(..., max_length=255)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: RoleEnum = Field(default=RoleEnum.USER)
    active: bool = Field(default=True)


class UserCreate(UserBase):
    """Schema for creating a new user – identical to UserBase."""

    pass


class UserUpdate(BaseModel):
    """
    Schema for updating an existing user. All fields are optional so that
    partial updates are supported. Only the fields explicitly sent in the
    request body will be applied (``exclude_unset=True`` is used in CRUD).
    """

    username: Optional[str] = Field(
        default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )
    email: Optional[EmailStr] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(
        default=None, min_length=1, max_length=100
    )
    last_name: Optional[str] = Field(
        default=None, min_length=1, max_length=100
    )
    role: Optional[RoleEnum] = None
    active: Optional[bool] = None


class UserResponse(BaseModel):
    """
    Schema returned by the API for a single user.

    Includes all database columns, including auto-generated fields like
    ``id``, ``created_at``, and ``updated_at``.

    The ``from_attributes = True`` config enables automatic conversion from
    SQLAlchemy ORM objects (replaces Pydantic v1's ``orm_mode``).
    """

    id: uuid.UUID
    username: str
    email: str
    first_name: str
    last_name: str
    role: RoleEnum
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """
    Schema returned by the ``GET /users`` list endpoint.

    Includes the matching users array alongside pagination metadata so
    clients can implement offset-based pagination.
    """

    users: list[UserResponse]
    total: int
    skip: int
    limit: int
