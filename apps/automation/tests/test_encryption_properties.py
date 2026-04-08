"""
Property-based tests for credential encryption.

Tests the TokenEncryption utility using Hypothesis to verify encryption
properties hold across a wide range of inputs.

Requirements: 2.6, 17.1
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from apps.automation.utils.encryption import TokenEncryption


# Strategy for generating random credentials
credentials_strategy = st.text(
    alphabet=st.characters(
        blacklist_categories=('Cs', 'Cc'),  # Exclude surrogates and control chars
        min_codepoint=32,
        max_codepoint=126
    ),
    min_size=1,
    max_size=500
)

# Strategy for auth types
auth_type_strategy = st.sampled_from(['oauth', 'meta', 'api_key'])


class TestCredentialEncryptionRoundTrip:
    """
    Property 1: Credential Encryption Round-Trip
    
    Validates: Requirements 2.6, 17.1
    
    Property: For any credential string and auth_type, encrypting then decrypting
    must return the original value.
    
    Mathematical property: decrypt(encrypt(x, t), t) = x for all x, t
    """
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_encryption_key):
        """Setup encryption keys for all tests."""
        TokenEncryption.reset()
        yield
        TokenEncryption.reset()
    
    @given(
        credential=credentials_strategy,
        auth_type=auth_type_strategy
    )
    @settings(
        max_examples=100,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_encrypt_decrypt_returns_original(
        self,
        credential: str,
        auth_type: str
    ):
        """
        Test that encrypt/decrypt round-trip returns original credential.
        
        Property: decrypt(encrypt(credential, auth_type), auth_type) == credential
        
        Args:
            credential: Random credential string
            auth_type: Authentication type (oauth, meta, api_key)
        """
        # Encrypt the credential
        encrypted = TokenEncryption.encrypt(credential, auth_type)
        
        # Verify encrypted is bytes
        assert isinstance(encrypted, bytes), "Encrypted value must be bytes"
        
        # Verify encrypted is not empty for non-empty input
        if credential:
            assert len(encrypted) > 0, "Encrypted value must not be empty"
        
        # Decrypt the credential
        decrypted = TokenEncryption.decrypt(encrypted, auth_type)
        
        # Verify round-trip property
        assert decrypted == credential, (
            f"Round-trip failed for auth_type={auth_type}: "
            f"original={repr(credential)}, decrypted={repr(decrypted)}"
        )
    
    @given(
        credential=credentials_strategy,
        auth_type=auth_type_strategy
    )
    @settings(
        max_examples=50,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_encrypt_produces_different_output(
        self,
        credential: str,
        auth_type: str
    ):
        """
        Test that encryption produces different output than input.
        
        Property: encrypt(credential, auth_type) != credential (for non-empty input)
        
        Args:
            credential: Random credential string
            auth_type: Authentication type
        """
        # Skip empty credentials
        assume(len(credential) > 0)
        
        # Encrypt the credential
        encrypted = TokenEncryption.encrypt(credential, auth_type)
        
        # Verify encrypted output is different from input
        assert encrypted != credential.encode(), (
            "Encrypted output should differ from plaintext input"
        )
    
    @given(
        credential=credentials_strategy,
        auth_type=auth_type_strategy
    )
    @settings(
        max_examples=50,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_multiple_encryptions_produce_different_ciphertexts(
        self,
        credential: str,
        auth_type: str
    ):
        """
        Test that encrypting the same credential twice produces different ciphertexts.
        
        This verifies that Fernet uses proper IV/nonce for each encryption.
        
        Property: encrypt(x, t) != encrypt(x, t) (probabilistically)
        
        Args:
            credential: Random credential string
            auth_type: Authentication type
        """
        # Skip empty credentials
        assume(len(credential) > 0)
        
        # Encrypt the same credential twice
        encrypted1 = TokenEncryption.encrypt(credential, auth_type)
        encrypted2 = TokenEncryption.encrypt(credential, auth_type)
        
        # Verify different ciphertexts (Fernet uses random IV)
        assert encrypted1 != encrypted2, (
            "Multiple encryptions of same plaintext should produce different ciphertexts"
        )
        
        # But both should decrypt to the same value
        decrypted1 = TokenEncryption.decrypt(encrypted1, auth_type)
        decrypted2 = TokenEncryption.decrypt(encrypted2, auth_type)
        
        assert decrypted1 == credential
        assert decrypted2 == credential
    
    def test_empty_string_round_trip(self):
        """
        Test that empty string encrypts and decrypts correctly.
        
        Edge case: Empty credentials should be handled gracefully.
        """
        for auth_type in ['oauth', 'meta', 'api_key']:
            encrypted = TokenEncryption.encrypt('', auth_type)
            assert encrypted == b'', "Empty string should encrypt to empty bytes"
            
            decrypted = TokenEncryption.decrypt(b'', auth_type)
            assert decrypted == '', "Empty bytes should decrypt to empty string"
    
    @given(
        credential=credentials_strategy,
        correct_auth_type=auth_type_strategy,
        wrong_auth_type=auth_type_strategy
    )
    @settings(
        max_examples=50,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_wrong_auth_type_fails_decryption(
        self,
        credential: str,
        correct_auth_type: str,
        wrong_auth_type: str
    ):
        """
        Test that using wrong auth_type for decryption fails.
        
        Property: decrypt(encrypt(x, t1), t2) should fail when t1 != t2
        
        This validates Requirement 17.4: Different auth_types use different keys.
        
        Args:
            credential: Random credential string
            correct_auth_type: Auth type used for encryption
            wrong_auth_type: Different auth type used for decryption
        """
        # Skip if auth types are the same
        assume(correct_auth_type != wrong_auth_type)
        
        # Skip empty credentials
        assume(len(credential) > 0)
        
        # Encrypt with correct auth type
        encrypted = TokenEncryption.encrypt(credential, correct_auth_type)
        
        # Attempt to decrypt with wrong auth type should fail
        with pytest.raises(ValueError, match="Decryption failed"):
            TokenEncryption.decrypt(encrypted, wrong_auth_type)
    
    @given(credential=credentials_strategy)
    @settings(
        max_examples=30,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_all_auth_types_work_independently(
        self,
        credential: str
    ):
        """
        Test that all three auth types can encrypt/decrypt independently.
        
        Property: Each auth_type maintains its own encryption/decryption cycle.
        
        Args:
            credential: Random credential string
        """
        auth_types = ['oauth', 'meta', 'api_key']
        encrypted_values = {}
        
        # Encrypt with each auth type
        for auth_type in auth_types:
            encrypted = TokenEncryption.encrypt(credential, auth_type)
            encrypted_values[auth_type] = encrypted
            
            # Verify immediate decryption works
            decrypted = TokenEncryption.decrypt(encrypted, auth_type)
            assert decrypted == credential, (
                f"Round-trip failed for {auth_type}"
            )
        
        # Verify each auth type can still decrypt its own value
        for auth_type in auth_types:
            decrypted = TokenEncryption.decrypt(
                encrypted_values[auth_type],
                auth_type
            )
            assert decrypted == credential, (
                f"Delayed decryption failed for {auth_type}"
            )


class TestEncryptionEdgeCases:
    """Test edge cases and error conditions for encryption."""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_encryption_key):
        """Setup encryption keys for all tests."""
        TokenEncryption.reset()
        yield
        TokenEncryption.reset()
    
    def test_decrypt_invalid_ciphertext(self):
        """Test that decrypting invalid ciphertext raises error."""
        invalid_ciphertext = b'not_valid_fernet_token'
        
        with pytest.raises(ValueError, match="Decryption failed"):
            TokenEncryption.decrypt(invalid_ciphertext, 'oauth')
    
    def test_decrypt_corrupted_ciphertext(self):
        """Test that decrypting corrupted ciphertext raises error."""
        # Encrypt a valid credential
        encrypted = TokenEncryption.encrypt('test_credential', 'oauth')
        
        # Corrupt the ciphertext
        corrupted = encrypted[:-5] + b'xxxxx'
        
        # Decryption should fail
        with pytest.raises(ValueError, match="Decryption failed"):
            TokenEncryption.decrypt(corrupted, 'oauth')
    
    @given(credential=st.text(min_size=1, max_size=10000))
    @settings(
        max_examples=20,
        deadline=2000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_large_credentials(self, credential: str):
        """Test that large credentials can be encrypted and decrypted."""
        encrypted = TokenEncryption.encrypt(credential, 'oauth')
        decrypted = TokenEncryption.decrypt(encrypted, 'oauth')
        
        assert decrypted == credential
    
    @given(
        credential=st.text(
            alphabet=st.characters(min_codepoint=0, max_codepoint=0x10FFFF),
            min_size=1,
            max_size=100
        )
    )
    @settings(
        max_examples=30,
        deadline=1000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    def test_unicode_credentials(self, credential: str):
        """Test that Unicode credentials are handled correctly."""
        encrypted = TokenEncryption.encrypt(credential, 'oauth')
        decrypted = TokenEncryption.decrypt(encrypted, 'oauth')
        
        assert decrypted == credential
