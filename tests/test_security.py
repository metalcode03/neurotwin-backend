"""
Security-focused tests for the credit-based AI architecture.

Covers:
  22.1  API key encryption / decryption
  22.2  PII sanitization
  22.3  Rate limiting
  22.4  RBAC (admin-only endpoints)
  22.5  Input validation

Requirements: 22.1-22.9
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# --------------- 22.1  Encryption ---------------

class TestEncryption:
    """Test Fernet encryption utility."""

    def test_encrypt_and_decrypt_round_trip(self):
        """Encrypting then decrypting should return the original text."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            from apps.core.encryption import encrypt, decrypt
            original = 'sk-cerebras-super-secret-api-key-123'
            ciphertext = encrypt(original)

            assert ciphertext != original, "Ciphertext must differ from plaintext"
            assert decrypt(ciphertext) == original

    def test_encrypt_empty_raises(self):
        """Encrypting an empty string should raise ValueError."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            from apps.core.encryption import encrypt
            with pytest.raises(ValueError, match="empty"):
                encrypt('')

    def test_decrypt_bad_token_raises(self):
        """Decrypting garbage should raise ValueError."""
        from cryptography.fernet import Fernet
        test_key = Fernet.generate_key().decode()

        with patch.dict(os.environ, {'ENCRYPTION_KEY': test_key}):
            from apps.core.encryption import decrypt
            with pytest.raises(ValueError, match="Decryption failed"):
                decrypt('not-a-valid-fernet-token')

    def test_missing_key_raises(self):
        """Missing ENCRYPTION_KEY env var should raise EnvironmentError."""
        with patch.dict(os.environ, {}, clear=True):
            # Force re-import to pick up new env
            from apps.core import encryption
            import importlib
            importlib.reload(encryption)
            with pytest.raises(EnvironmentError, match="ENCRYPTION_KEY"):
                encryption.encrypt('hello')


# --------------- 22.2  PII Sanitization ---------------

class TestPIISanitization:
    """Test PII redaction helper."""

    def test_email_redacted(self):
        from apps.credits.utils import sanitize_prompt_for_logging
        text = "Send an email to john.doe@example.com about the meeting"
        result = sanitize_prompt_for_logging(text)
        assert 'john.doe@example.com' not in result
        assert '[EMAIL_REDACTED]' in result

    def test_phone_redacted(self):
        from apps.credits.utils import sanitize_prompt_for_logging
        text = "Call me at +1-555-123-4567 or (555) 987-6543"
        result = sanitize_prompt_for_logging(text)
        assert '555-123-4567' not in result
        assert '[PHONE_REDACTED]' in result

    def test_credit_card_redacted(self):
        from apps.credits.utils import sanitize_prompt_for_logging
        text = "My card number is 4111 1111 1111 1111"
        result = sanitize_prompt_for_logging(text)
        assert '4111' not in result
        assert '[CC_REDACTED]' in result

    def test_ssn_redacted(self):
        from apps.credits.utils import sanitize_prompt_for_logging
        text = "SSN is 123-45-6789"
        result = sanitize_prompt_for_logging(text)
        assert '123-45-6789' not in result
        assert '[SSN_REDACTED]' in result

    def test_empty_string_passthrough(self):
        from apps.credits.utils import sanitize_prompt_for_logging
        assert sanitize_prompt_for_logging('') == ''
        assert sanitize_prompt_for_logging(None) is None

    def test_no_pii_unchanged(self):
        from apps.credits.utils import sanitize_prompt_for_logging
        text = "Summarize the quarterly report for me"
        assert sanitize_prompt_for_logging(text) == text


# --------------- 22.3  Rate Limiting ---------------

class TestCreditRateThrottle:
    """Test that CreditRateThrottle is configured correctly."""

    def test_throttle_scope_and_rate(self):
        from apps.credits.throttling import CreditRateThrottle
        throttle = CreditRateThrottle()
        assert throttle.scope == 'credits'
        assert throttle.rate == '100/hour'


# --------------- 22.4  RBAC / Permissions ---------------

class TestIsAdminUserPermission:
    """Test custom IsAdminUser permission class."""

    def test_staff_user_allowed(self):
        from apps.credits.permissions import IsAdminUser
        perm = IsAdminUser()
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = True

        assert perm.has_permission(request, view=None) is True

    def test_non_staff_user_denied(self):
        from apps.credits.permissions import IsAdminUser
        perm = IsAdminUser()
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_staff = False

        assert perm.has_permission(request, view=None) is False

    def test_anonymous_user_denied(self):
        from apps.credits.permissions import IsAdminUser
        perm = IsAdminUser()
        request = MagicMock()
        request.user.is_authenticated = False
        request.user.is_staff = False

        assert perm.has_permission(request, view=None) is False


# --------------- 22.5  Input Validation ---------------

class TestInputValidation:
    """Test input validation functions."""

    def test_valid_brain_mode_accepted(self):
        from apps.credits.validators import validate_brain_mode
        assert validate_brain_mode('brain') == 'brain'
        assert validate_brain_mode('brain_pro') == 'brain_pro'
        assert validate_brain_mode('brain_gen') == 'brain_gen'

    def test_invalid_brain_mode_rejected(self):
        from rest_framework.exceptions import ValidationError
        from apps.credits.validators import validate_brain_mode
        with pytest.raises(ValidationError, match="Invalid brain_mode"):
            validate_brain_mode('super_brain')

    def test_valid_operation_type_accepted(self):
        from apps.credits.validators import validate_operation_type
        assert validate_operation_type('simple_response') == 'simple_response'
        assert validate_operation_type('automation') == 'automation'

    def test_invalid_operation_type_rejected(self):
        from rest_framework.exceptions import ValidationError
        from apps.credits.validators import validate_operation_type
        with pytest.raises(ValidationError, match="Invalid operation_type"):
            validate_operation_type('magic')

    def test_positive_integer_valid(self):
        from apps.credits.validators import validate_positive_integer
        assert validate_positive_integer(100) == 100
        assert validate_positive_integer('42') == 42

    def test_positive_integer_zero_rejected(self):
        from rest_framework.exceptions import ValidationError
        from apps.credits.validators import validate_positive_integer
        with pytest.raises(ValidationError, match="positive integer"):
            validate_positive_integer(0)

    def test_positive_integer_negative_rejected(self):
        from rest_framework.exceptions import ValidationError
        from apps.credits.validators import validate_positive_integer
        with pytest.raises(ValidationError, match="positive integer"):
            validate_positive_integer(-5)

    def test_date_range_valid(self):
        from datetime import datetime
        from apps.credits.validators import validate_date_range
        s = datetime(2024, 1, 1)
        e = datetime(2024, 12, 31)
        assert validate_date_range(s, e) == (s, e)

    def test_date_range_reversed_rejected(self):
        from datetime import datetime
        from rest_framework.exceptions import ValidationError
        from apps.credits.validators import validate_date_range
        with pytest.raises(ValidationError, match="start_date"):
            validate_date_range(datetime(2024, 12, 31), datetime(2024, 1, 1))
