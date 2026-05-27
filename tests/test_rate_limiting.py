"""
Rate limiting integration tests.

These tests require ``RATE_LIMIT_ENABLED=true`` so that slowapi
decorators and middleware are active. Run them via the dedicated
docker-compose service:

    docker-compose run --rm test-rate-limit
"""

import uuid

import pytest

from app import models
from app.limiter import reset_limiter


@pytest.fixture(autouse=True)
def _clear_rate_limits():
    """Reset the in-memory rate limiter storage before every test."""
    reset_limiter()


class TestPostRateLimit:
    """Verify POST /users is rate-limited to 20 requests per minute."""

    def test_create_20_users_succeeds(self, client):
        """The first 20 POST requests in a window return 201."""
        for i in range(20):
            payload = {
                "username": f"ratelimit{i}",
                "email": f"ratelimit{i}@example.com",
                "first_name": "Rate",
                "last_name": f"Limit{i}",
            }
            response = client.post("/users", json=payload)
            assert response.status_code == 201, (
                f"Request {i + 1} expected 201, got {response.status_code}"
            )

    def test_21st_request_returns_429(self, client):
        """The 21st POST within a minute should return 429 Too Many Requests."""
        # Saturate the rate limit with 20 successful requests
        for i in range(20):
            payload = {
                "username": f"rlsat{i}",
                "email": f"rlsat{i}@example.com",
                "first_name": "Sat",
                "last_name": f"User{i}",
            }
            response = client.post("/users", json=payload)
            assert response.status_code == 201

        # 21st request must be rejected
        response = client.post(
            "/users",
            json={
                "username": "blocked_user",
                "email": "blocked@example.com",
                "first_name": "Blocked",
                "last_name": "User",
            },
        )
        assert response.status_code == 429


class TestDeleteRateLimit:
    """Verify DELETE /users/{id} is rate-limited to 10 requests per minute."""

    def test_delete_11_users_returns_429_on_last(self, client, db_session):
        """After 10 successful deletes, the 11th must return 429."""
        # Seed 11 users directly in the database to avoid POST rate limiting
        user_ids = []
        for i in range(11):
            user = models.User(
                username=f"deltest{i}",
                email=f"deltest{i}@example.com",
                first_name="Del",
                last_name=f"Test{i}",
            )
            db_session.add(user)
            db_session.flush()  # populate user.id
            user_ids.append(str(user.id))
        db_session.commit()

        # First 10 deletes succeed
        for user_id in user_ids[:10]:
            response = client.delete(f"/users/{user_id}")
            assert response.status_code == 200, (
                f"Delete {user_id} expected 200, got {response.status_code}"
            )

        # 11th delete hits the rate limit
        response = client.delete(f"/users/{user_ids[10]}")
        assert response.status_code == 429, (
            f"Expected 429, got {response.status_code}. "
            f"Headers: {dict(response.headers)}"
        )


class TestDeactivateRateLimit:
    """Verify PATCH /users/{id}/deactivate is rate-limited to 10/minute."""

    def test_deactivate_11_users_returns_429_on_last(self, client, db_session):
        """After 10 successful deactivations, the 11th must return 429."""
        # Seed 11 users directly
        user_ids = []
        for i in range(11):
            user = models.User(
                username=f"deactest{i}",
                email=f"deactest{i}@example.com",
                first_name="Deac",
                last_name=f"Test{i}",
            )
            db_session.add(user)
            db_session.flush()
            user_ids.append(str(user.id))
        db_session.commit()

        for user_id in user_ids[:10]:
            response = client.patch(f"/users/{user_id}/deactivate")
            assert response.status_code == 200

        response = client.patch(f"/users/{user_ids[10]}/deactivate")
        assert response.status_code == 429


class TestHealthNoRateLimit:
    """Verify health check is never rate-limited."""

    def test_many_health_checks_all_succeed(self, client):
        """Sending 50 health checks should all return 200."""
        for i in range(50):
            response = client.get("/health")
            assert response.status_code == 200, (
                f"Health check {i + 1} expected 200, got {response.status_code}"
            )
