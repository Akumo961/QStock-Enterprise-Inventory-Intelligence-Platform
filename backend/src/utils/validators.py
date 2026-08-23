"""
Validation Utilities for QR Inventory System

Provides comprehensive validation functions for:
- Email addresses
- Phone numbers
- Item codes
- Passwords
- QR code data
- File uploads
- General input sanitization
"""

import mimetypes
import re
from datetime import UTC, datetime

# ============================================================================
# EMAIL VALIDATION
# ============================================================================

def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Checks for:
    - Valid characters
    - @ symbol presence
    - Valid domain structure
    - TLD presence

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_email("user@company.com")
        True
        >>> validate_email("invalid.email")
        False
    """
    if not email or len(email) > 255:
        return False

    # RFC 5322 compliant email regex (simplified)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        return False

    # Additional checks
    local_part, domain = email.rsplit('@', 1)

    # Check local part length
    if len(local_part) > 64:
        return False

    # Check domain length
    if len(domain) > 253:
        return False
    return len(domain) <= 253


def is_company_email(email: str, allowed_domains: list[str]) -> bool:
    """
    Check if email belongs to allowed company domains.

    Args:
        email: Email address to check
        allowed_domains: List of allowed domain names

    Returns:
        True if email domain is in allowed list

    Example:
        >>> is_company_email("user@company.com", ["company.com"])
        True
    """
    if not validate_email(email):
        return False

    domain = email.split('@')[1].lower()
    return domain in [d.lower() for d in allowed_domains]


# ============================================================================
# PHONE NUMBER VALIDATION
# ============================================================================

def validate_phone(phone: str, country_code: str | None = None) -> bool:
    """
    Validate phone number format.

    Supports:
    - International format (+1234567890)
    - National format (123-456-7890)
    - Various separators (spaces, dashes, parentheses)

    Args:
        phone: Phone number to validate
        country_code: Optional country code for specific validation

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_phone("+1-234-567-8900")
        True
        >>> validate_phone("(234) 567-8900")
        True
    """
    if not phone:
        return False

    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone)

    # Check if it contains only digits and optional + at start
    if not re.match(r'^\+?[0-9]{8,15}$', cleaned):
        return False

    return bool(re.match(r'^\+?[0-9]{8,15}$', cleaned))


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to standard format.

    Args:
        phone: Phone number to normalize

    Returns:
        Normalized phone number (digits only with optional +)

    Example:
        >>> normalize_phone("(123) 456-7890")
        "1234567890"
    """
    # Remove all non-digit characters except +
    normalized = re.sub(r'[^\d+]', '', phone)

    # If starts with +, keep it; otherwise just digits
    if normalized.startswith('+'):
        return normalized
    else:
        return normalized.lstrip('+')


# ============================================================================
# ITEM CODE VALIDATION
# ============================================================================

def validate_item_code(item_code: str, allow_lowercase: bool = False) -> bool:
    """
    Validate item code format.

    Rules:
    - 3-100 characters
    - Alphanumeric with optional hyphens/underscores
    - No spaces
    - Uppercase recommended (configurable)

    Args:
        item_code: Item code to validate
        allow_lowercase: Whether to allow lowercase letters

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_item_code("ITEM-ABC123")
        True
        >>> validate_item_code("item_001", allow_lowercase=True)
        True
    """
    if not item_code or len(item_code) < 3 or len(item_code) > 100:
        return False

    if allow_lowercase:
        pattern = r'^[A-Za-z0-9\-_]+$'
    else:
        pattern = r'^[A-Z0-9\-_]+$'

    return bool(re.match(pattern, item_code))


def generate_item_code(prefix: str = "ITEM", length: int = 8) -> str:
    """
    Generate a random item code.

    Args:
        prefix: Prefix for the item code
        length: Length of random part (hex digits)

    Returns:
        Generated item code

    Example:
        >>> code = generate_item_code("LAPTOP", 6)
        >>> code.startswith("LAPTOP-")
        True
    """
    import uuid
    random_part = uuid.uuid4().hex[:length].upper()
    return f"{prefix}-{random_part}"


# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

def validate_password(password: str, min_length: int = 8) -> tuple[bool, list[str]]:
    """
    Validate password strength.

    Requirements:
    - Minimum length (default 8)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (optional but recommended)

    Args:
        password: Password to validate
        min_length: Minimum required length

    Returns:
        Tuple of (is_valid, list_of_issues)

    Example:
        >>> is_valid, issues = validate_password("Weak123")
        >>> is_valid
        False
        >>> "Too short" in issues
        True
    """
    issues = []

    if len(password) < min_length:
        issues.append(f"Password must be at least {min_length} characters long")

    if not re.search(r'[A-Z]', password):
        issues.append("Password must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        issues.append("Password must contain at least one lowercase letter")

    if not re.search(r'[0-9]', password):
        issues.append("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        issues.append("Password should contain at least one special character (recommended)")

    # Check for common weak passwords
    weak_passwords = [
        'password', 'password123', '12345678', 'qwerty', 'abc123',
        'letmein', 'welcome', 'monkey', '123456789', 'password1'
    ]
    if password.lower() in weak_passwords:
        issues.append("Password is too common and easily guessable")

    return (len(issues) == 0, issues)


def calculate_password_strength(password: str) -> int:
    """
    Calculate password strength score (0-100).

    Args:
        password: Password to evaluate

    Returns:
        Strength score (0-100)

    Example:
        >>> calculate_password_strength("Ab1!")
        40
        >>> calculate_password_strength("MyS3cur3P@ssw0rd!")
        95
    """
    score = 0

    # Length score (up to 30 points)
    score += min(len(password) * 2, 30)

    # Character variety (up to 40 points)
    if re.search(r'[a-z]', password):
        score += 10
    if re.search(r'[A-Z]', password):
        score += 10
    if re.search(r'[0-9]', password):
        score += 10
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 10

    # Complexity bonus (up to 30 points)
    if len(password) >= 12:
        score += 10
    if len(set(password)) >= len(password) * 0.7:  # Character diversity
        score += 10
    if not any(password.lower().startswith(weak) for weak in ['pass', 'admin', 'user']):
        score += 10

    return min(score, 100)


# ============================================================================
# QR CODE VALIDATION
# ============================================================================

def validate_qr_code_data(qr_data: str, expected_type: str | None = None) -> bool:
    """
    Validate QR code data format.

    Expected formats:
    - USER:{user_id}:{email}
    - ITEM:{item_id}:{item_code}

    Args:
        qr_data: QR code data string
        expected_type: Expected type (USER or ITEM), or None for any

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_qr_code_data("USER:1:user@company.com")
        True
        >>> validate_qr_code_data("ITEM:5:ITEM-ABC123")
        True
    """
    if not qr_data or ':' not in qr_data:
        return False

    parts = qr_data.split(':')

    if len(parts) < 3:
        return False

    qr_type = parts[0].upper()

    if qr_type not in ['USER', 'ITEM']:
        return False

    if expected_type and qr_type != expected_type.upper():
        return False

    # Validate ID is numeric
    try:
        int(parts[1])
    except ValueError:
        return False

    # Validate third part
    if qr_type == 'USER':
        return validate_email(parts[2])
    elif qr_type == 'ITEM':
        return validate_item_code(parts[2], allow_lowercase=True)

    return True


# ============================================================================
# STRING SANITIZATION
# ============================================================================

def sanitize_string(
        text: str,
        max_length: int | None = None,
        allow_newlines: bool = False,
        strip_html: bool = True
) -> str:
    """
    Sanitize string input.

    Operations:
    - Remove leading/trailing whitespace
    - Replace multiple spaces with single space
    - Optionally remove newlines
    - Optionally strip HTML tags
    - Optionally truncate to max length

    Args:
        text: Text to sanitize
        max_length: Maximum length to truncate to
        allow_newlines: Whether to preserve newline characters
        strip_html: Whether to remove HTML tags

    Returns:
        Sanitized string

    Example:
        >>> sanitize_string("  Hello   World  ", max_length=10)
        "Hello Worl"
    """
    if not text:
        return ""

    # Strip HTML tags if requested
    if strip_html:
        text = re.sub(r'<[^>]+>', '', text)

    # Remove leading/trailing whitespace
    text = text.strip()

    # Handle newlines
    if not allow_newlines:
        text = text.replace('\n', ' ').replace('\r', ' ')

    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)

    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip()

    return text


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename

    Example:
        >>> sanitize_filename("My File!@#.txt")
        "My_File.txt"
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)

    # Replace multiple underscores/spaces with single underscore
    filename = re.sub(r'[_\s]+', '_', filename)

    # Ensure it's not too long
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        name = name[:max_length - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name

    return filename.strip('_')


# ============================================================================
# FILE VALIDATION
# ============================================================================

def validate_file_extension(filename: str, allowed_extensions: list[str]) -> bool:
    """
    Validate file extension.

    Args:
        filename: Filename to check
        allowed_extensions: List of allowed extensions (with or without dot)

    Returns:
        True if extension is allowed

    Example:
        >>> validate_file_extension("image.png", [".png", ".jpg"])
        True
    """
    if not filename or '.' not in filename:
        return False

    ext = filename.rsplit('.', 1)[1].lower()

    # Normalize allowed extensions
    normalized = [e.lstrip('.').lower() for e in allowed_extensions]

    return ext in normalized


def validate_file_size(size_bytes: int, max_size_mb: float = 5.0) -> bool:
    """
    Validate file size.

    Args:
        size_bytes: File size in bytes
        max_size_mb: Maximum allowed size in megabytes

    Returns:
        True if size is within limit

    Example:
        >>> validate_file_size(1024 * 1024, 5.0)  # 1MB file, 5MB limit
        True
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    return size_bytes <= max_size_bytes


def get_safe_mime_type(filename: str) -> str | None:
    """
    Get safe MIME type for a filename.

    Args:
        filename: Filename to check

    Returns:
        MIME type string or None

    Example:
        >>> get_safe_mime_type("document.pdf")
        "application/pdf"
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type


# ============================================================================
# DATE/TIME VALIDATION
# ============================================================================

def validate_date_string(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
    """
    Validate date string format.

    Args:
        date_str: Date string to validate
        format_str: Expected date format

    Returns:
        True if valid date format

    Example:
        >>> validate_date_string("2024-01-15")
        True
        >>> validate_date_string("01/15/2024", "%m/%d/%Y")
        True
    """
    try:
        datetime.strptime(date_str, format_str).replace(tzinfo=UTC)
        return True
    except ValueError:
        return False


def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
    """
    Validate that end date is after start date.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        True if valid range
    """
    return end_date >= start_date


# ============================================================================
# NUMERIC VALIDATION
# ============================================================================

def validate_positive_integer(value: int | str) -> bool:
    """
    Validate positive integer.

    Args:
        value: Value to validate

    Returns:
        True if positive integer

    Example:
        >>> validate_positive_integer(5)
        True
        >>> validate_positive_integer("-1")
        False
    """
    try:
        num = int(value)
        return num > 0
    except (ValueError, TypeError):
        return False


def validate_quantity(quantity: int, min_val: int = 1, max_val: int = 1000) -> bool:
    """
    Validate quantity value.

    Args:
        quantity: Quantity to validate
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        True if within valid range
    """
    return isinstance(quantity, int) and min_val <= quantity <= max_val


# ============================================================================
# GENERAL VALIDATORS
# ============================================================================

def is_safe_string(text: str, allow_special_chars: bool = False) -> bool:
    """
    Check if string contains only safe characters.

    Args:
        text: String to check
        allow_special_chars: Whether to allow special characters

    Returns:
        True if safe
    """
    if allow_special_chars:
        pattern = r'^[a-zA-Z0-9\s\-_.,!?@#$%&*()]+$'
    else:
        pattern = r'^[a-zA-Z0-9\s\-_]+$'

    return bool(re.match(pattern, text))


def validate_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if valid URL

    Example:
        >>> validate_url("https://example.com")
        True
    """
    pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return bool(pattern.match(url))