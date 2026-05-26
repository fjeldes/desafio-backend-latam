import uuid
import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import schemas, crud
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=schemas.UserListResponse,
    summary="List all users",
    description="Retrieve a paginated list of users with optional filtering by active status and role.",
)
def list_users(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        default=100, ge=1, le=100, description="Maximum number of records to return"
    ),
    active: bool | None = Query(
        default=None, description="Filter by active status"
    ),
    role: str | None = Query(
        default=None, description="Filter by role (admin, user, guest)"
    ),
    db: Session = Depends(get_db),
):
    users, total = crud.get_users(db, skip=skip, limit=limit, active=active, role=role)
    return schemas.UserListResponse(
        users=users, total=total, skip=skip, limit=limit
    )


@router.get(
    "/{user_id}",
    response_model=schemas.UserResponse,
    summary="Get a user by ID",
    description="Retrieve a single user by their unique identifier.",
)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return crud.get_user_by_id(db, user_id)


@router.post(
    "",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user with the provided data. Username and email must be unique.",
)
def create_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db),
):
    return crud.create_user(db, user_data)


@router.put(
    "/{user_id}",
    response_model=schemas.UserResponse,
    summary="Update a user",
    description="Update all fields of an existing user. Username and email must be unique.",
)
def update_user(
    user_id: uuid.UUID,
    user_data: schemas.UserUpdate,
    db: Session = Depends(get_db),
):
    return crud.update_user(db, user_id, user_data)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a user",
    description="Permanently delete a user by their unique identifier.",
)
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return crud.delete_user(db, user_id)


@router.patch(
    "/{user_id}/deactivate",
    response_model=schemas.UserResponse,
    summary="Deactivate a user",
    description="Deactivate a user by setting their active status to false.",
)
def deactivate_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return crud.deactivate_user(db, user_id)
