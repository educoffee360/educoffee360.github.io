from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

ph = PasswordHasher()

def hash_password(password: str) -> str:
    return ph.hash(str)

def verify_password(hashed_password: str, plain_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except VerificationError:
        return False

def needs_rehash(hashed_password: str) -> bool:
    return ph.check_needs_rehash(hashed_password)
