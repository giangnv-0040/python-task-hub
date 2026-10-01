from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_not_plaintext() -> None:
    hashed = hash_password("Password123")
    assert hashed != "Password123"


def test_verify_password_ok_and_wrong() -> None:
    hashed = hash_password("Password123")
    assert verify_password("Password123", hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_create_and_decode_access_token_roundtrip() -> None:
    token = create_access_token(subject="alice")
    assert decode_access_token(token) == "alice"


def test_decode_access_token_invalid_returns_none() -> None:
    assert decode_access_token("not-a-valid-token") is None


def test_decode_access_token_expired_returns_none() -> None:
    issued_at = datetime.now(timezone.utc) - timedelta(hours=1)
    expired_payload = {
        "sub": "alice",
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=1),
    }
    expired_token = jwt.encode(
        expired_payload, settings.secret_key, algorithm=settings.jwt_algorithm
    )
    assert decode_access_token(expired_token) is None


def test_decode_access_token_signed_with_other_secret_returns_none() -> None:
    forged = jwt.encode(
        {"sub": "alice"}, "another-secret", algorithm=settings.jwt_algorithm
    )
    assert decode_access_token(forged) is None


def test_decode_access_token_non_string_sub_returns_none() -> None:
    # Chu ky hop le nhung sub sai kieu -> phai la "token khong hop le", khong 500
    token = jwt.encode({"sub": 123}, settings.secret_key, algorithm=settings.jwt_algorithm)
    assert decode_access_token(token) is None


def test_create_access_token_has_expiry() -> None:
    claims = jwt.get_unverified_claims(create_access_token(subject="alice"))
    lifetime = claims["exp"] - claims["iat"]
    assert lifetime == settings.access_token_expire_minutes * 60
