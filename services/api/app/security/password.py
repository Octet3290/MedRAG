import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with an automatically generated salt.
    Bcrypt is an adaptive key-derivation function that protects against rainbow table
    and hardware-accelerated brute-force attacks.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash in constant time
    to prevent timing side-channel attacks.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False
