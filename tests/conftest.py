"""
Pytest fixtures and configuration for the User Management API test suite.

Sets up an isolated SQLite database for each test so that tests do not
interfere with each other or with the local development database.

Fixtures
--------
setup_db       : Autouse – drops and recreates all tables before every test.
db_session     : Provides a raw SQLAlchemy session for direct DB access.
client         : FastAPI TestClient with the DB dependency overridden.
sample_user    : Convenience fixture that creates a user via the API.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import get_db
from app.main import app
from app.models import Base

# In-memory / file-based SQLite database dedicated to tests.
# Using a file-based URL ("sqlite:///./test.db") because in-memory databases
# are destroyed when the engine disconnects, which causes issues with the
# autouse fixture that opens and closes connections per test.
TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """
    FastAPI dependency override that returns a session connected to the
    test database instead of the production/SQLite one.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """
    Autouse fixture: drops and recreates all tables before and after
    every test function. This guarantees a clean database state.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """
    Provides a raw SQLAlchemy session for tests that need to interact
    with the database directly (e.g. inserting test data without going
    through the API).
    """
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """
    Provides a synchronous TestClient that talks to the FastAPI app
    with the database dependency overridden to use the test database.
    """
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    # Clean up the override after the test so it doesn't leak
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(client):
    """
    Creates a user via the API and returns the JSON response.
    Useful for tests that need an existing user to operate on
    (e.g. GET /users/{id}, PUT, DELETE, PATCH deactivate).
    """
    payload = {
        "username": "jperez",
        "email": "juan@example.com",
        "first_name": "Juan",
        "last_name": "Perez",
        "role": "user",
        "active": True,
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    return response.json()
