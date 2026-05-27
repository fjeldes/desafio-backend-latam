"""
CRUD (Create, Read, Update, Delete) operations for the User model.

This module contains all business logic for interacting with user records
in the database. It is called by the route handlers in ``app.routes``.

Each function receives a SQLAlchemy session and returns either a domain
object or a Pydantic schema – never a FastAPI Response directly.
"""

import uuid
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exc

from app import models, schemas

logger = logging.getLogger(__name__)


def _handle_integrity_error(
    db: Session,
    e: exc.IntegrityError,
    username: str | None = None,
    email: str | None = None,
):
    """
    Parse a SQLAlchemy IntegrityError and raise the appropriate HTTPException.

    Rolls back the failed transaction and inspects the original database
    error to determine whether the conflict was caused by a duplicate
    username, duplicate email, or an unknown constraint violation.

    Parameters
    ----------
    db : Session
        The active database session (will be rolled back).
    e : IntegrityError
        The caught exception.
    username : str or None
        The username that may have caused the conflict.
    email : str or None
        The email that may have caused the conflict.

    Raises
    ------
    HTTPException (409)
        Always raised with a descriptive detail message indicating
        which field caused the conflict.
    """
    db.rollback()

    error_msg = str(e.orig).lower() if e.orig else ""

    if username and "username" in error_msg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{username}' already exists",
        )

    if email and "email" in error_msg:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{email}' already exists",
        )

    # Fallback for unexpected integrity violations
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Username or email already exists",
    )


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    active: bool | None = None,
    role: str | None = None,
) -> list[models.User]:
    """
    Retrieve a paginated, optionally filtered list of users.

    Parameters
    ----------
    db : Session
        Active database session.
    skip : int
        Number of records to offset (default 0).
    limit : int
        Max records to return (1-100, default 100).
    active : bool or None
        If set, filter by the ``active`` column.
    role : str or None
        If set, filter by the ``role`` column (e.g. "admin", "user", "guest").

    Returns
    -------
    tuple[list[User], int]
        A tuple containing the list of matching User objects and the total
        count (before pagination).
    """
    query = db.query(models.User)

    # Apply optional filters
    if active is not None:
        query = query.filter(models.User.active == active)
    if role is not None:
        query = query.filter(models.User.role == role)

    # total = count of all matching rows (respects filters, ignores offset/limit)
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return users, total


def get_user_by_id(db: Session, user_id: uuid.UUID) -> models.User:
    """
    Retrieve a single user by their unique ID.

    Raises
    ------
    HTTPException (404)
        If no user with the given ``user_id`` exists.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found",
        )
    return user


def create_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    """
    Insert a new user into the database.

    The ``UserCreate`` schema is converted to a ``User`` ORM instance using
    ``model_dump()``, which unpacks all validated fields as keyword arguments.

    Raises
    ------
    HTTPException (409)
        If the username or email is already taken. The detail message
        indicates which field caused the conflict.
    """
    # Convert validated Pydantic data to a SQLAlchemy model instance
    db_user = models.User(**user_data.model_dump())

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)  # populate auto-generated fields (id, timestamps)
        logger.info(f"User created: {db_user.id}")
        return db_user

    except exc.IntegrityError as e:
        _handle_integrity_error(
            db, e, username=user_data.username, email=user_data.email
        )


def update_user(
    db: Session, user_id: uuid.UUID, user_data: schemas.UserUpdate
) -> models.User:
    """
    Update one or more fields of an existing user.

    Uses ``exclude_unset=True`` so that only the fields explicitly provided
    in the JSON body are applied. The rest remain unchanged.

    Raises
    ------
    HTTPException (404)
        If the user does not exist.
    HTTPException (400)
        If ``user_data`` contains no fields at all.
    HTTPException (409)
        If the update would create a duplicate username or email.
    """
    # Ensure the user exists before attempting any update
    user = get_user_by_id(db, user_id)

    # Build a dict of only the fields the client actually sent
    update_dict = user_data.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        # Dynamically apply each field to the ORM object
        for field, value in update_dict.items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)
        logger.info(f"User updated: {user.id}")
        return user

    except exc.IntegrityError as e:
        _handle_integrity_error(
            db,
            e,
            username=update_dict.get("username"),
            email=update_dict.get("email"),
        )


def delete_user(db: Session, user_id: uuid.UUID) -> dict:
    """
    Permanently remove a user from the database.

    Returns a confirmation dictionary with a user-friendly message.
    The user must exist; otherwise a 404 is raised.
    """
    user = get_user_by_id(db, user_id)
    db.delete(user)
    db.commit()
    logger.info(f"User deleted: {user.id}")
    return {"detail": f"User '{user_id}' deleted successfully"}


def deactivate_user(db: Session, user_id: uuid.UUID) -> models.User:
    """
    Soft-deactivate a user by setting ``active = False``.

    The user record remains in the database but appears as inactive in
    list/search results unless explicitly filtered.

    Returns the updated User object.
    """
    user = get_user_by_id(db, user_id)
    user.active = False
    db.commit()
    db.refresh(user)
    logger.info(f"User deactivated: {user.id}")
    return user
