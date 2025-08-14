import re

def is_valid_email(email: str) -> bool:
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def is_blank(field: str) -> bool:
    return not field or field.strip() == ""