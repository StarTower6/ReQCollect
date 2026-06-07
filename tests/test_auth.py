"""Tests for auth module: JWT and password hashing."""

from datetime import timedelta

import pytest

from app.core.auth import (
    create_access_token,
    verify_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pwd = "test-password-123"
        h = hash_password(pwd)
        assert h != pwd
        assert verify_password(pwd, h) is True

    def test_wrong_password(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False


class TestJWT:
    def test_create_and_verify(self):
        token = create_access_token({"sub": "user123"})
        assert isinstance(token, str)
        assert len(token) > 20

        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"

    def test_expired_token(self):
        token = create_access_token(
            {"sub": "user123"},
            expires_delta=timedelta(seconds=-1),
        )
        payload = verify_token(token)
        assert payload is None

    def test_bad_token(self):
        payload = verify_token("invalid.token.here")
        assert payload is None

    def test_custom_expires(self):
        token = create_access_token(
            {"sub": "test"},
            expires_delta=timedelta(hours=1),
        )
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test"
