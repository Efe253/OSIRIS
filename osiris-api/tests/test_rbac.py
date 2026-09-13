"""RBAC testleri — roller, anahtarlar, hiyerarşi."""

import pytest
from osiris_api.auth import (
    ROLES,
    create_token,
    hash_api_key,
    role_satisfies,
    verify_token_with_role,
)

SECRET = "rbac-test-secret"


def test_role_hierarchy() -> None:
    assert role_satisfies("admin", "viewer")
    assert role_satisfies("admin", "analyst")
    assert role_satisfies("analyst", "viewer")
    assert not role_satisfies("viewer", "analyst")
    assert not role_satisfies("viewer", "admin")
    assert not role_satisfies("bilinmeyen", "viewer")
    assert not role_satisfies("admin", "bilinmeyen-esik")


def test_hash_deterministic_and_salted_by_value() -> None:
    assert hash_api_key("abc") == hash_api_key("abc")
    assert hash_api_key("abc") != hash_api_key("abd")
    assert len(hash_api_key("abc")) == 64
    with pytest.raises(ValueError):
        hash_api_key("")


def test_token_role_roundtrip() -> None:
    for role in ROLES:
        token = create_token("u", SECRET, role=role)["access_token"]
        assert verify_token_with_role(token, SECRET) == ("u", role)


def test_token_default_role_viewer_and_bad_role() -> None:
    token = create_token("u", SECRET)["access_token"]
    assert verify_token_with_role(token, SECRET) == ("u", "viewer")
    with pytest.raises(ValueError):
        create_token("u", SECRET, role="superadmin")


def test_token_unknown_role_rejected() -> None:
    import base64
    import hashlib
    import hmac
    import json

    def b64(o):
        return base64.urlsafe_b64encode(
            json.dumps(o, separators=(",", ":")).encode()).rstrip(b"=").decode()

    h = b64({"alg": "HS256", "typ": "JWT"})
    c = b64({"iss": "osiris", "sub": "u", "role": "root",
             "iat": 1, "exp": 9999999999})
    sig = base64.urlsafe_b64encode(
        hmac.new(SECRET.encode(), f"{h}.{c}".encode(),
                 hashlib.sha256).digest()).rstrip(b"=").decode()
    with pytest.raises(ValueError):
        verify_token_with_role(f"{h}.{c}.{sig}", SECRET)
