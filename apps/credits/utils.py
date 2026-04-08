"""
Utility functions for credit management.

Requirements: 22.4
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------- PII Detection Patterns ----------

_PII_PATTERNS = [
    # Email addresses
    (re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'), '[EMAIL_REDACTED]'),
    # Phone numbers (international and US formats)
    (re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'), '[PHONE_REDACTED]'),
    # Credit card numbers (Visa, MC, Amex, Discover – with optional separators)
    (re.compile(r'\b(?:\d[ -]*?){13,19}\b'), '[CC_REDACTED]'),
    # Social Security Numbers
    (re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'), '[SSN_REDACTED]'),
]


def sanitize_prompt_for_logging(text: str) -> str:
    """
    Remove personally-identifiable information from *text* before it is
    persisted in the AIRequestLog table.

    Applies regex-based redaction for:
      • Email addresses
      • Phone numbers
      • Credit-card numbers
      • Social Security Numbers

    Requirements: 22.4
    """
    if not text:
        return text

    sanitized = text
    for pattern, replacement in _PII_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized
