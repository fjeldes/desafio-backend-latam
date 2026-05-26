import uuid
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import exc

from app import models, schemas

logger = logging.getLogger(__name__)


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    active: bool | None = None,
    role: str | None = None,
) -> list[models.User]:
    query = db.query(models.User)
    if active is not None:
        query = query.filter(models.User.active == active)
    if role is not None:
        query = query.filter(models.User.role == role)
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return users, total


def get_user_by_id(db: Session, user_id: uuid.UUID) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found",
        )
    return user


def create_user(db: Session, user_data: schemas.UserCreate) -> models.User:
    db_user = models.User(**user_data.model_dump())
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User created: {db_user.id}")
        return db_user
    except exc.IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig).lower() if e.orig else ""
        if "username" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{user_data.username}' already exists",
            )
        if "email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{user_data.email}' already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )


def update_user(
    db: Session, user_id: uuid.UUID, user_data: schemas.UserUpdate
) -> models.User:
    user = get_user_by_id(db, user_id)
    update_dict = user_data.model_dump(exclude_unset=True)

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        for field, value in update_dict.items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)
        logger.info(f"User updated: {user.id}")
        return user
    except exc.IntegrityError as e:
        db.rollback()
        error_msg = str(e.orig).lower() if e.orig else ""
        if "username" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{update_dict.get('username')}' already exists",
            )
        if "email" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{update_dict.get('email')}' already exists",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )


def delete_user(db: Session, user_id: uuid.UUID) -> dict:
    user = get_user_by_id(db, user_id)
    db.delete(user)
    db.commit()
    logger.info(f"User deleted: {user.id}")
    return {"detail": f"User '{user_id}' deleted successfully"}


def deactivate_user(db: Session, user_id: uuid.UUID) -> models.User:
    user = get_user_by_id(db, user_id)
    user.active = False
    db.commit()
    db.refresh(user)
    logger.info(f"User deactivated: {user.id}")
    return user
