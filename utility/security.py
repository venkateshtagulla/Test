"""
Password security helpers.
"""
from typing import AnyStr

import bcrypt


def hash_password(password: AnyStr) -> str:
    """
    Hash a plain-text password using bcrypt.
    """

    encoded_password = password if isinstance(password, bytes) else password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(encoded_password, salt).decode("utf-8")


def verify_password(raw_password: AnyStr, hashed_password: str) -> bool:
    """
    Validate a plain password against a hash.
    """

    encoded_password = raw_password if isinstance(raw_password, bytes) else raw_password.encode("utf-8")
    return bcrypt.checkpw(encoded_password, hashed_password.encode("utf-8"))

