import uuid


class TestHealthCheck:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCreateUser:
    def test_create_user_success(self, client):
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
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_user_default_values(self, client):
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
        payload = {
            "username": "jperez",
            "email": "other@example.com",
            "first_name": "Other",
            "last_name": "User",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 409
        assert "jperez" in response.json()["detail"]

    def test_create_user_duplicate_email(self, client, sample_user):
        payload = {
            "username": "newuser",
            "email": "juan@example.com",
            "first_name": "New",
            "last_name": "User",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 409

    def test_create_user_invalid_email(self, client):
        payload = {
            "username": "baduser",
            "email": "not-an-email",
            "first_name": "Bad",
            "last_name": "Email",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 422

    def test_create_user_short_username(self, client):
        payload = {
            "username": "ab",
            "email": "ab@example.com",
            "first_name": "Short",
            "last_name": "User",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 422

    def test_create_user_invalid_username_chars(self, client):
        payload = {
            "username": "user name!",
            "email": "bad@example.com",
            "first_name": "Bad",
            "last_name": "Chars",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 422

    def test_create_user_missing_required_fields(self, client):
        payload = {"username": "test"}
        response = client.post("/users", json=payload)
        assert response.status_code == 422

    def test_create_user_invalid_role(self, client):
        payload = {
            "username": "testrole",
            "email": "testrole@example.com",
            "first_name": "Test",
            "last_name": "Role",
            "role": "manager",
        }
        response = client.post("/users", json=payload)
        assert response.status_code == 422


class TestGetUser:
    def test_get_user_success(self, client, sample_user):
        user_id = sample_user["id"]
        response = client.get(f"/users/{user_id}")
        assert response.status_code == 200
        assert response.json()["id"] == user_id

    def test_get_user_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = client.get(f"/users/{fake_id}")
        assert response.status_code == 404


class TestListUsers:
    def test_list_users_empty(self, client):
        response = client.get("/users")
        assert response.status_code == 200
        data = response.json()
        assert data["users"] == []
        assert data["total"] == 0

    def test_list_users_with_data(self, client, sample_user):
        response = client.get("/users")
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) == 1
        assert data["total"] == 1

    def test_list_users_pagination(self, client, sample_user):
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
        response = client.get("/users?active=true")
        assert response.status_code == 200
        data = response.json()
        assert all(u["active"] for u in data["users"])

    def test_list_users_filter_by_role(self, client, sample_user):
        response = client.get("/users?role=user")
        assert response.status_code == 200
        data = response.json()
        assert all(u["role"] == "user" for u in data["users"])


class TestUpdateUser:
    def test_update_user_success(self, client, sample_user):
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
        fake_id = str(uuid.uuid4())
        payload = {"first_name": "NoExist"}
        response = client.put(f"/users/{fake_id}", json=payload)
        assert response.status_code == 404

    def test_update_user_duplicate_username(self, client, sample_user):
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
        user_id = sample_user["id"]
        response = client.put(f"/users/{user_id}", json={})
        assert response.status_code == 400


class TestDeleteUser:
    def test_delete_user_success(self, client, sample_user):
        user_id = sample_user["id"]
        response = client.delete(f"/users/{user_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["detail"]
        get_response = client.get(f"/users/{user_id}")
        assert get_response.status_code == 404

    def test_delete_user_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/users/{fake_id}")
        assert response.status_code == 404


class TestDeactivateUser:
    def test_deactivate_user_success(self, client, sample_user):
        user_id = sample_user["id"]
        assert sample_user["active"] is True
        response = client.patch(f"/users/{user_id}/deactivate")
        assert response.status_code == 200
        assert response.json()["active"] is False

    def test_deactivate_user_not_found(self, client):
        fake_id = str(uuid.uuid4())
        response = client.patch(f"/users/{fake_id}/deactivate")
        assert response.status_code == 404
