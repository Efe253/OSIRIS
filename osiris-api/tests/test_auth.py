"""JWT auth testleri."""

import base64
import json

import pytest
from osiris_api.auth import create_token, verify_token

SECRET = "test-secret-123"


def _b64url(obj: object) -> str:
    return base64.urlsafe_b64encode(
        json.dumps(obj, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()


def test_roundtrip() -> None:
    token = create_token("istemci", SECRET)["access_token"]
    assert isinstance(token, str)
    assert verify_token(token, SECRET) == "istemci"


def test_wrong_secret_rejected() -> None:
    token = create_token("a", SECRET)["access_token"]
    with pytest.raises(ValueError):
        verify_token(token, "baska-secret")


def test_tampered_payload_rejected() -> None:
    token = create_token("a", SECRET)["access_token"]
    h, c, s = token.split(".")
    tampered = f"{h}.{_b64url({'iss': 'osiris', 'sub': 'admin', 'iat': 1, 'exp': 9999999999})}.{s}"
    with pytest.raises(ValueError):
        verify_token(tampered, SECRET)


def test_none_algorithm_rejected() -> None:
    fake = f"{_b64url({'alg': 'none', 'typ': 'JWT'})}.{_b64url({'sub': 'x'})}."
    with pytest.raises(ValueError):
        verify_token(fake, SECRET)


def test_expired_rejected() -> None:
    token = create_token("a", SECRET, ttl_seconds=60)["access_token"]
    h, c, s = token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(c + "=="))
    claims["exp"] = 1000  # geçmiş
    expired = f"{h}.{_b64url(claims)}.{s}"
    # imzayı da yenile ki yalnızca süre kontrolü test edilsin
    import hashlib
    import hmac

    sig = hmac.new(SECRET.encode(), f"{h}.{_b64url(claims)}".encode(),
                   hashlib.sha256).digest()
    expired = f"{h}.{_b64url(claims)}.{base64.urlsafe_b64encode(sig).rstrip(b'=').decode()}"
    with pytest.raises(ValueError, match="süresi"):
        verify_token(expired, SECRET)


def test_malformed_rejected() -> None:
    for bad in ["", "a.b", "a.b.c.d", "...", "x" * 9000]:
        with pytest.raises(ValueError):
            verify_token(bad, SECRET)


def test_create_requires_secret() -> None:
    with pytest.raises(ValueError):
        create_token("a", "")
