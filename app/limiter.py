"""
Shared rate limiter instance for FastAPI.

Uses slowapi with remote-address-based rate limiting. The limiter
instance is created here so it can be imported by both ``main.py``
(middleware/exception handler registration) and ``routes.py``
(per-endpoint rate limits) without circular imports.

Rate limits are enforced in-memory, which is suitable for single-
instance deployments. Cloud Run auto-scaling gives each instance
its own limiter window.

To disable rate limiting (e.g. during tests), set the environment
variable ``RATE_LIMIT_ENABLED=false``.
"""

import os
from functools import wraps

from slowapi import Limiter
from slowapi.util import get_remote_address

# Key function extracts client IP for per-address rate limiting.
# key_style="endpoint" groups requests by function name rather than URL path,
# so all DELETEs share the same counter regardless of the {user_id} value.
limiter = Limiter(key_func=get_remote_address, key_style="endpoint")

# Allow disabling rate limits for environments where they interfere
# (e.g. integration tests that issue many requests in sequence)
_RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"


def reset_limiter():
    """
    Clear all in-memory rate limit counters.

    Useful between tests to get a clean rate limit slate when
    multiple tests run in the same process with rate limiting enabled.
    """
    storage = getattr(limiter, "_storage", None)
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()


def rate_limit(value: str):
    """
    Decorator factory that conditionally applies a slowapi rate limit.

    If the ``RATE_LIMIT_ENABLED`` environment variable is set to
    ``"false"``, this returns a no-op decorator that simply calls the
    underlying function without any rate checking.

    Parameters
    ----------
    value : str
        A slowapi rate limit string (e.g. ``"20/minute"``).

    Returns
    -------
    Callable
        Either a slowapi ``limit`` decorator or a passthrough identity
        decorator, depending on ``RATE_LIMIT_ENABLED``.
    """

    def noop_decorator(func):
        """Passthrough decorator that does not enforce any rate limit."""
        return func

    if not _RATE_LIMIT_ENABLED:
        return noop_decorator

    return limiter.limit(value)
