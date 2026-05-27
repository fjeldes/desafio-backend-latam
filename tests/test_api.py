"""
Integration tests for the User Management API.

Uses FastAPI's TestClient to exercise every endpoint. The test database
is reset before each test via the autouse ``setup_db`` fixture defined
in ``conftest.py``.

Test classes are organized by endpoint to keep related scenarios together.
"""

import uuid


class TestHealthCheck:
    """Tests for the GET /health endpoint."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCreateUser:
    """Tests for the POST /users endpoint."""

    def test_create_user_success(self, client):
        """A valid payload should return 201 with the user's data."""
        payload = {
            "username": "jdoe",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "role": "user",
            "active": True,
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "jdoe"
        assert data["email"] == "john@example.com"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["role"] == "user"
        assert data["active"] is True
        # Auto-generated fields
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_user_default_values(self, client):
        """Omitting role and active should default to 'user' and True."""
        payload = {
            "username": "defaults",
            "email": "defaults@example.com",
            "first_name": "Test",
            "last_name": "User",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"
        assert data["active"] is True

    def test_create_user_duplicate_username(self, client, sample_user):
        """Reusing an existing username should return 409."""
        payload = {
            "username": "jperez",  # already used by sample_user
            "email": "other@example.com",
            "first_name": "Other",
            "last_name": "User",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 409
        assert "jperez" in response.json()["detail"]

    def test_create_user_duplicate_email(self, client, sample_user):
        """Reusing an existing email should return 409."""
        payload = {
            "username": "newuser",
            "email": "juan@example.com",  # already used by sample_user
            "first_name": "New",
            "last_name": "User",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 409

    def test_create_user_invalid_email(self, client):
        """A malformed email should be rejected with 422 (validation error)."""
        payload = {
            "username": "baduser",
            "email": "not-an-email",
            "first_name": "Bad",
            "last_name": "Email",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 422

    def test_create_user_short_username(self, client):
        """Username shorter than 3 characters should fail validation."""
        payload = {
            "username": "ab",
            "email": "ab@example.com",
            "first_name": "Short",
            "last_name": "User",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 422

    def test_create_user_invalid_username_chars(self, client):
        """Username with spaces/special chars should fail the regex pattern."""
        payload = {
            "username": "user name!",
            "email": "bad@example.com",
            "first_name": "Bad",
            "last_name": "Chars",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 422

    def test_create_user_missing_required_fields(self, client):
        """Missing required fields (email, first_name, last_name) should give 422."""
        payload = {"username": "test"}
        response = client.post("/users", json=payload)
        assert response.status_code == 422

    def test_create_user_invalid_role(self, client):
        """A role outside the allowed enum should fail validation."""
        payload = {
            "username": "testrole",
            "email": "testrole@example.com",
            "first_name": "Test",
            "last_name": "Role",
            "role": "manager",  # not in RoleEnum
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 422


class TestGetUser:
    """Tests for the GET /users/{id} endpoint."""

    def test_get_user_success(self, client, sample_user):
        """Querying an existing user by ID should return the full user record."""
        user_id = sample_user["id"]
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["id"] == user_id

    def test_get_user_not_found(self, client):
        """Querying a non-existent ID should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/users/{fake_id}")
        assert response.status_code == 404


class TestListUsers:
    """Tests for the GET /users endpoint (listing with pagination & filters)."""

    def test_list_users_empty(self, client):
        """Listing users on a fresh database should return an empty array."""
        response = client.get("/users")
        assert response.status_code == 200
        data = response.json()
        assert data["users"] == []
        assert data["total"] == 0

    def test_list_users_with_data(self, client, sample_user):
        """After creating a user, the list should contain it."""
        response = client.get("/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 1
        assert data["total"] == 1

    def test_list_users_pagination(self, client, sample_user):
        """Offset-based pagination should respect skip and limit params."""
        # Create 5 additional users (total 6 with sample_user)
        for i in range(5):
            client.post(
                "/users",
                json={
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                    "first_name": f"First{i}",
                    "last_name": f"Last{i}",
                },
            )
        response = client.get("/users?skip=0&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 3
        assert data["total"] == 6
        assert data["skip"] == 0
        assert data["limit"] == 3

    def test_list_users_filter_by_active(self, client, sample_user):
        """Filtering by active=true should only return active users."""
        response = client.get("/users?active=true")
        assert response.status_code == 200
        data = response.json()
        assert all(u["active"] for u in data["users"])

    def test_list_users_filter_by_role(self, client, sample_user):
        """Filtering by role=user should only return users with that role."""
        response = client.get("/users?role=user")
        assert response.status_code == 200
        data = response.json()
        assert all(u["role"] == "user" for u in data["users"])


class TestUpdateUser:
    """Tests for the PUT /users/{id} endpoint."""

    def test_update_user_success(self, client, sample_user):
        """Updating only first/last name should leave other fields unchanged."""
        user_id = sample_user["id"]
        payload = {
            "first_name": "Juan Carlos",
            "last_name": "Perez Gomez",
        }
        response = client.put(f"/users/{user_id}", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Juan Carlos"
        assert data["last_name"] == "Perez Gomez"
        assert data["username"] == "jperez"  # unchanged

    def test_update_user_not_found(self, client):
        """Updating a non-existent ID should return 404."""
        fake_id = str(uuid.uuid4())
        payload = {"first_name": "NoExist"}
        response = client.put(f"/users/{fake_id}", json=payload)
        assert response.status_code == 404

    def test_update_user_duplicate_username(self, client, sample_user):
        """Setting a username that belongs to another user should return 409."""
        # Create a second user to trigger the conflict
        client.post(
            "/users",
            json={
                "username": "existing",
                "email": "existing@example.com",
                "first_name": "Existing",
                "last_name": "User",
            },
        )
        user_id = sample_user["id"]
        response = client.put(f"/users/{user_id}", json={"username": "existing"})
        assert response.status_code == 409

    def test_update_user_empty_body(self, client, sample_user):
        """Sending an empty JSON object should return 400."""
        user_id = sample_user["id"]
        response = client.put(f"/users/{user_id}", json={})
        assert response.status_code == 400


class TestDeleteUser:
    """Tests for the DELETE /users/{id} endpoint."""

    def test_delete_user_success(self, client, sample_user):
        """Deleting a user should succeed and the user should no longer exist."""
        user_id = sample_user["id"]
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["detail"]

        # Subsequent GET should return 404
        get_response = client.get(f"/users/{user_id}")
        assert get_response.status_code == 404

    def test_delete_user_not_found(self, client):
        """Deleting a non-existent ID should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/users/{fake_id}")
        assert response.status_code == 404


class TestDeactivateUser:
    """Tests for the PATCH /users/{id}/deactivate endpoint."""

    def test_deactivate_user_success(self, client, sample_user):
        """Deactivating a user should set active=False."""
        user_id = sample_user["id"]
        assert sample_user["active"] is True
        response = client.patch(f"/users/{user_id}/deactivate")
        assert response.status_code == 200
        assert response.json()["active"] is False

    def test_deactivate_user_not_found(self, client):
        """Deactivating a non-existent ID should return 404."""
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/users/{fake_id}/deactivate")
        assert response.status_code == 404
