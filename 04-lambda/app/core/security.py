"""Security utilities for password generation, hashing, etc."""

import secrets
import string


def generate_secure_password(length: int = 32) -> str:
    """
    Generate a cryptographically secure random password.
    
    Args:
        length: Password length (default: 32)
        
    Returns:
        Secure random password
        
    Examples:
        >>> password = generate_secure_password()
        >>> len(password)
        32
        
        >>> password = generate_secure_password(length=64)
        >>> len(password)
        64
    """
    # Use all printable ASCII characters except some special chars that can cause issues
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_api_key(prefix: str = "sk", length: int = 48) -> str:
    """
    Generate an API key with a prefix.
    
    Args:
        prefix: Key prefix (default: "sk")
        length: Random part length (default: 48)
        
    Returns:
        API key in format "prefix-random"
        
    Examples:
        >>> api_key = generate_api_key()
        >>> api_key.startswith("sk-")
        True
    """
    random_part = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(length)
    )
    return f"{prefix}-{random_part}"


def generate_token(length: int = 32) -> str:
    """
    Generate a URL-safe random token.
    
    Args:
        length: Token length in bytes (output will be longer due to base64 encoding)
        
    Returns:
        URL-safe token
        
    Examples:
        >>> token = generate_token()
        >>> len(token) > 0
        True
    """
    return secrets.token_urlsafe(length)
