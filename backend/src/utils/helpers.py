"""
Helper Utilities for QR Inventory System

Provides utility functions for:
- Date/time operations
- String formatting
- Pagination
- File operations
- Report generation
- Data transformations
"""

import csv
import hashlib
import io
from datetime import UTC, datetime, timedelta
from typing import Any, Generic, TypeVar

# Type variable for generic pagination
T = TypeVar('T')


# ============================================================================
# DATE AND TIME HELPERS
# ============================================================================

def calculate_days_between(
        start_date: datetime,
        end_date: datetime | None = None
) -> int:
    """
    Calculate the number of days between two dates.

    Args:
        start_date: Start date
        end_date: End date (defaults to current UTC time)

    Returns:
        Number of days as integer

    Example:
        >>> from datetime import datetime
        >>> start = datetime(2024, 1, 1)
        >>> end = datetime(2024, 1, 8)
        >>> calculate_days_between(start, end)
        7
    """
    if end_date is None:
        end_date = datetime.now(UTC)

    delta = end_date - start_date
    return delta.days


def is_overdue(due_date: datetime | None) -> bool:
    """
    Check if a due date has passed.

    Args:
        due_date: Due date to check (None returns False)

    Returns:
        True if overdue, False otherwise

    Example:
        >>> from datetime import datetime, timedelta
        >>> past_date = datetime.now(UTC) - timedelta(days=1)
        >>> is_overdue(past_date)
        True
    """
    if due_date is None:
        return False

    return datetime.now(UTC) > due_date


def days_until_due(due_date: datetime | None) -> int | None:
    """
    Calculate days until due date.

    Args:
        due_date: Due date

    Returns:
        Number of days (negative if overdue, None if no due date)

    Example:
        >>> from datetime import datetime, timedelta
        >>> future = datetime.now(UTC) + timedelta(days=5)
        >>> days_until_due(future)
        5
    """
    if due_date is None:
        return None

    delta = due_date - datetime.now(UTC)
    return delta.days


def format_duration(
        start_date: datetime,
        end_date: datetime | None = None,
        short_format: bool = False
) -> str:
    """
    Format duration between two dates as human-readable string.

    Args:
        start_date: Start date
        end_date: End date (defaults to now)
        short_format: Use short format (e.g., "5d" vs "5 days")

    Returns:
        Formatted duration string

    Examples:
        >>> from datetime import datetime, timedelta
        >>> start = datetime.now(UTC)- timedelta(days=3)
        >>> format_duration(start)
        "3 days"
        >>> format_duration(start, short_format=True)
        "3d"
    """
    days = calculate_days_between(start_date, end_date)

    if days == 0:
        return "today" if not short_format else "0d"
    elif days == 1:
        return "1 day" if not short_format else "1d"
    elif days < 7:
        return f"{days} days" if not short_format else f"{days}d"
    elif days < 30:
        weeks = days // 7
        suffix = "week" if weeks == 1 else "weeks"
        return f"{weeks} {suffix}" if not short_format else f"{weeks}w"
    elif days < 365:
        months = days // 30
        suffix = "month" if months == 1 else "months"
        return f"{months} {suffix}" if not short_format else f"{months}mo"
    else:
        years = days // 365
        suffix = "year" if years == 1 else "years"
        return f"{years} {suffix}" if not short_format else f"{years}y"


def format_datetime(
        dt: datetime,
        format_type: str = "default"
) -> str:
    """
    Format datetime for display.

    Args:
        dt: Datetime to format
        format_type: Format type (default, short, long, iso)

    Returns:
        Formatted datetime string

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2024, 1, 15, 14, 30)
        >>> format_datetime(dt, "default")
        "Jan 15, 2024 2:30 PM"
    """
    formats = {
        "default": "%b %d, %Y %I:%M %p",
        "short": "%m/%d/%y %H:%M",
        "long": "%A, %B %d, %Y at %I:%M %p",
        "iso": "%Y-%m-%dT%H:%M:%S",
        "date_only": "%Y-%m-%d",
        "time_only": "%H:%M:%S"
    }

    format_str = formats.get(format_type, formats["default"])
    return dt.strftime(format_str)


def get_date_range(
        range_type: str,
        start_date: datetime | None = None
) -> tuple[datetime, datetime]:
    """
    Get date range for common periods.

    Args:
        range_type: Range type (today, week, month, quarter, year)
        start_date: Optional start date (defaults to now)

    Returns:
        Tuple of (start_datetime, end_datetime)

    Example:
        >>> start, end = get_date_range("week")
        >>> (end - start).days
        7
    """
    if start_date is None:
        start_date = datetime.now(UTC)

    ranges = {
        "today": timedelta(days=1),
        "week": timedelta(days=7),
        "month": timedelta(days=30),
        "quarter": timedelta(days=90),
        "year": timedelta(days=365)
    }

    delta = ranges.get(range_type, timedelta(days=1))
    end_date = start_date + delta

    return (start_date, end_date)


# ============================================================================
# STRING FORMATTING HELPERS
# ============================================================================

def truncate_string(
        text: str,
        max_length: int,
        suffix: str = "..."
) -> str:
    """
    Truncate string to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated

    Returns:
        Truncated string

    Example:
        >>> truncate_string("This is a long text", 10)
        "This is..."
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def format_file_size(size_bytes: int, precision: int = 2) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes
        precision: Decimal precision

    Returns:
        Formatted size string

    Examples:
        >>> format_file_size(1024)
        "1.00 KB"
        >>> format_file_size(1048576)
        "1.00 MB"
    """
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    return f"{size:.{precision}f} {units[unit_index]}"


def slugify(text: str, separator: str = "-") -> str:
    """
    Convert string to URL-friendly slug.

    Args:
        text: Text to slugify
        separator: Separator character

    Returns:
        Slugified string

    Example:
        >>> slugify("Hello World! 123")
        "hello-world-123"
    """
    import re

    # Convert to lowercase
    text = text.lower()

    # Replace spaces and special characters with separator
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', separator, text)
    text = re.sub(r'^-+|-+$', '', text)

    return text


def title_case(text: str) -> str:
    """
    Convert string to title case (smart capitalization).

    Args:
        text: Text to convert

    Returns:
        Title-cased string

    Example:
        >>> title_case("hello world")
        "Hello World"
    """
    # Words that should stay lowercase
    lowercase_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for',
                       'in', 'of', 'on', 'or', 'the', 'to', 'with'}

    words = text.split()
    result = []

    for i, word in enumerate(words):
        if i == 0 or word.lower() not in lowercase_words:
            result.append(word.capitalize())
        else:
            result.append(word.lower())

    return ' '.join(result)


# ============================================================================
# PAGINATION HELPERS
# ============================================================================

class PaginationParams:
    """Pagination parameters container."""

    def __init__(self, page: int = 1, page_size: int = 50):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), 100)  # Max 100 items per page

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.page_size


def paginate_query(query, page: int, page_size: int):
    """
    Apply pagination to SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Paginated query

    Example:
        >>> from sqlalchemy.orm import Session
        >>> query = session.query(User)
        >>> paginated = paginate_query(query, 2, 10)
    """
    params = PaginationParams(page, page_size)
    return query.offset(params.offset).limit(params.limit)


def calculate_total_pages(total_items: int, page_size: int) -> int:
    """
    Calculate total number of pages.

    Args:
        total_items: Total number of items
        page_size: Items per page

    Returns:
        Total pages

    Example:
        >>> calculate_total_pages(95, 10)
        10
    """
    import math
    return math.ceil(total_items / page_size) if total_items > 0 else 1


class PaginatedResponse(Generic[T]):
    """Generic paginated response container."""

    def __init__(
            self,
            items: list[T],
            total: int,
            page: int,
            page_size: int
    ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = calculate_total_pages(total, page_size)
        self.has_next = page < self.total_pages
        self.has_prev = page > 1


# ============================================================================
# FILE AND DATA HELPERS
# ============================================================================

def generate_filename(
        prefix: str,
        extension: str,
        timestamp: bool = True
) -> str:
    """
    Generate a unique filename.

    Args:
        prefix: Filename prefix
        extension: File extension (with or without dot)
        timestamp: Include timestamp in filename

    Returns:
        Generated filename

    Example:
        >>> filename = generate_filename("report", "pdf")
        >>> filename.startswith("report_")
        True
    """
    extension = extension.lstrip('.')

    if timestamp:
        timestamp_str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp_str}.{extension}"
    else:
        import uuid
        unique_id = uuid.uuid4().hex[:8]
        return f"{prefix}_{unique_id}.{extension}"


def generate_report_filename(report_type: str, extension: str = "pdf") -> str:
    """
    Generate a filename for a report.

    Args:
        report_type: Type of report (e.g., "inventory", "transactions")
        extension: File extension

    Returns:
        Generated filename

    Example:
        >>> generate_report_filename("inventory", "xlsx")
        "inventory_report_20240115_143000.xlsx"
    """
    return generate_filename(f"{report_type}_report", extension, timestamp=True)


def read_csv_to_dict(csv_content: str) -> list[dict[str, Any]]:
    """
    Parse CSV content to list of dictionaries.

    Args:
        csv_content: CSV content as string

    Returns:
        List of dictionaries (one per row)
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    return list(reader)


def dict_to_csv(data: list[dict[str, Any]]) -> str:
    """
    Convert list of dictionaries to CSV string.

    Args:
        data: List of dictionaries

    Returns:
        CSV string
    """
    if not data:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)

    return output.getvalue()


# ============================================================================
# HASHING AND ENCODING HELPERS
# ============================================================================

def generate_hash(data: str, algorithm: str = "sha256") -> str:
    """
    Generate hash of data.

    Args:
        data: Data to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)

    Returns:
        Hex digest of hash

    Example:
        >>> generate_hash("test data")
        "916f0027a575074ce72a331777c3478d6513f786a591bd892da1a577bf2335f9"
    """
    hash_func = getattr(hashlib, algorithm)()
    hash_func.update(data.encode('utf-8'))
    return hash_func.hexdigest()


def generate_unique_id(prefix: str = "", length: int = 16) -> str:
    """
    Generate a unique ID.

    Args:
        prefix: Optional prefix
        length: Length of random part

    Returns:
        Unique ID string

    Example:
        >>> uid = generate_unique_id("user", 8)
        >>> uid.startswith("user_")
        True
    """
    import uuid
    unique_part = uuid.uuid4().hex[:length]

    if prefix:
        return f"{prefix}_{unique_part}"
    return unique_part


# ============================================================================
# DATA TRANSFORMATION HELPERS
# ============================================================================

def flatten_dict(
        d: dict[str, Any],
        parent_key: str = '',
        separator: str = '_'
) -> dict[str, Any]:
    """
    Flatten nested dictionary.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        separator: Key separator

    Returns:
        Flattened dictionary

    Example:
        >>> nested = {"user": {"name": "John", "age": 30}}
        >>> flatten_dict(nested)
        {"user_name": "John", "user_age": 30}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{separator}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, separator).items())
        else:
            items.append((new_key, v))

    return dict(items)


def safe_get(
        dictionary: dict[str, Any],
        key_path: str,
        default: Any = None,
        separator: str = '.'
) -> Any:
    """
    Safely get nested dictionary value using dot notation.

    Args:
        dictionary: Dictionary to search
        key_path: Dot-separated key path
        default: Default value if not found
        separator: Key separator

    Returns:
        Value or default

    Example:
        >>> data = {"user": {"profile": {"name": "John"}}}
        >>> safe_get(data, "user.profile.name")
        "John"
        >>> safe_get(data, "user.profile.age", default=0)
        0
    """
    keys = key_path.split(separator)
    value = dictionary

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default

    return value


def group_by(items: list[dict[str, Any]], key: str) -> dict[Any, list[dict[str, Any]]]:
    """
    Group list of dictionaries by key.

    Args:
        items: List of dictionaries
        key: Key to group by

    Returns:
        Dictionary with grouped items

    Example:
        >>> items = [{"type": "A", "val": 1}, {"type": "A", "val": 2}, {"type": "B", "val": 3}]
        >>> result = group_by(items, "type")
        >>> len(result["A"])
        2
    """
    from collections import defaultdict
    grouped = defaultdict(list)

    for item in items:
        if key in item:
            grouped[item[key]].append(item)

    return dict(grouped)


# ============================================================================
# UTILITY HELPERS
# ============================================================================

def chunk_list(lst: list[Any], chunk_size: int) -> list[list[Any]]:
    """
    Split list into chunks.

    Args:
        lst: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks

    Example:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def deduplicate_list(lst: list[Any], key: str | None = None) -> list[Any]:
    """
    Remove duplicates from list.

    Args:
        lst: List to deduplicate
        key: Optional key function for complex objects

    Returns:
        List without duplicates

    Example:
        >>> deduplicate_list([1, 2, 2, 3, 1])
        [1, 2, 3]
    """
    if key:
        seen = set()
        result = []
        for item in lst:
            k = item.get(key) if isinstance(item, dict) else getattr(item, key, None)
            if k not in seen:
                seen.add(k)
                result.append(item)
        return result
    else:
        return list(dict.fromkeys(lst))


def percentage(part: float, total: float, precision: int = 2) -> float:
    """
    Calculate percentage.

    Args:
        part: Part value
        total: Total value
        precision: Decimal precision

    Returns:
        Percentage value

    Example:
        >>> percentage(25, 100)
        25.0
    """
    if total == 0:
        return 0.0

    return round((part / total) * 100, precision)


def clamp(value: float, min_val: float, max_val: float) -> int | float:
    """
    Clamp value between min and max.

    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value

    Returns:
        Clamped value

    Example:
        >>> clamp(15, 0, 10)
        10
    """
    return max(min_val, min(max_val, value))