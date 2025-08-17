import re
import secrets, string

ALPHABET62 = string.ascii_letters + string.digits

def is_valid_email(email: str) -> bool:
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def is_blank(field: str) -> bool:
    return not field or field.strip() == ""

def generate_code(length: int = 8) -> str:
    return ''.join(secrets.choice(ALPHABET62) for _ in range(length))