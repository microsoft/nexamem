"""
Unit tests for Policy module - PolicyEngine, PIIDetector, and policy enforcement
"""
from unittest.mock import Mock

import pytest

from nexamem import ChannelConfig, MemoryScope
from nexamem.policy import (
    EncryptionRequired,
    PIIDetector,
    PolicyEngine,
    QuotaExceeded,
    TTLViolation,
)


class TestPIIDetector:
    """Test suite for PIIDetector class."""

    def test_detect_email(self):
        """Test email PII detection."""
        detector = PIIDetector()

        # Test cases with emails
        text_with_email = "Contact us at support@example.com for help"
        result = detector.detect_pii(text_with_email)
        assert result["email"] is True

        # Test without emails
        text_without_email = "Contact us for help with your account"
        result = detector.detect_pii(text_without_email)
        assert result["email"] is False

    def test_detect_phone(self):
        """Test phone number PII detection."""
        detector = PIIDetector()

        # Various phone number formats
        phone_formats = [
            "Call me at 555-123-4567",
            "My number is (555) 123-4567",
            "Phone: 555.123.4567",
            "Contact: +1-555-123-4567",
            "Number is 5551234567"
        ]

        for text in phone_formats:
            result = detector.detect_pii(text)
            assert result["phone"] is True, f"Failed to detect phone in: {text}"

        # Text without phone
        text_without_phone = "Call me later today"
        result = detector.detect_pii(text_without_phone)
        assert result["phone"] is False

    def test_detect_ssn(self):
        """Test SSN PII detection."""
        detector = PIIDetector()

        # Text with SSN
        text_with_ssn = "My SSN is 123-45-6789"
        result = detector.detect_pii(text_with_ssn)
        assert result["ssn"] is True

        # Text without SSN
        text_without_ssn = "My account number is 123456789"
        result = detector.detect_pii(text_without_ssn)
        assert result["ssn"] is False

    def test_detect_credit_card(self):
        """Test credit card PII detection."""
        detector = PIIDetector()

        # Various credit card formats
        cc_formats = [
            "Card number: 1234-5678-9012-3456",
            "Credit card: 1234 5678 9012 3456",
            "CC: 1234567890123456"
        ]

        for text in cc_formats:
            result = detector.detect_pii(text)
            assert result["credit_card"] is True, f"Failed to detect CC in: {text}"

        # Text without credit card
        text_without_cc = "Account balance is 1234"
        result = detector.detect_pii(text_without_cc)
        assert result["credit_card"] is False

    def test_detect_multiple_pii_types(self):
        """Test detection of multiple PII types in one text."""
        detector = PIIDetector()

        text = "Contact John at john@example.com or call 555-123-4567"
        result = detector.detect_pii(text)

        assert result["email"] is True
        assert result["phone"] is True
        assert result["ssn"] is False
        assert result["credit_card"] is False

    def test_has_any_pii(self):
        """Test has_any_pii method."""
        detector = PIIDetector()

        # Text with PII
        text_with_pii = "Email me at test@example.com"
        assert detector.has_any_pii(text_with_pii) is True

        # Text without PII
        text_without_pii = "This is just normal text"
        assert detector.has_any_pii(text_without_pii) is False

    def test_custom_patterns(self):
        """Test PIIDetector with custom patterns."""
        custom_patterns = {
            "custom_id": r"ID-\d{6}",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        }

        detector = PIIDetector(patterns=custom_patterns)

        # Test custom pattern
        text = "Your ID is ID-123456"
        result = detector.detect_pii(text)
        assert result["custom_id"] is True

        # Test that only custom patterns are used
        assert len(result) == 2  # Only custom_id and email

    def test_case_insensitive_detection(self):
        """Test that PII detection is case insensitive."""
        detector = PIIDetector()

        text = "Email: TEST@EXAMPLE.COM"
        result = detector.detect_pii(text)
        assert result["email"] is True

    def test_empty_text(self):
        """Test PII detection with empty text."""
        detector = PIIDetector()

        result = detector.detect_pii("")
        for _pii_type, detected in result.items():
            assert detected is False

    def test_none_text(self):
        """Test PII detection with None input."""
        detector = PIIDetector()

        with pytest.raises(TypeError):
            detector.detect_pii(None)


class TestPolicyEngine:
    """Test suite for PolicyEngine class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456",
            env="test"
        )

        self.channel_config = ChannelConfig(
            name="test_channel",
            ttl_sec=3600,
            encrypt=True,
            quota_bytes=1000000
        )

        self.mock_redis = Mock()
        self.policy_engine = PolicyEngine(redis_client=self.mock_redis)

    def test_validate_ttl_within_limit(self):
        """Test TTL validation when override is within channel limit."""
        # Should not raise exception
        self.policy_engine.validate_ttl(
            ttl_override=1800,  # 30 minutes
            channel_config=self.channel_config  # 1 hour limit
        )

    def test_validate_ttl_exceeds_limit(self):
        """Test TTL validation when override exceeds channel limit."""
        with pytest.raises(TTLViolation):
            self.policy_engine.validate_ttl(
                ttl_override=7200,  # 2 hours
                channel_config=self.channel_config  # 1 hour limit
            )

    def test_validate_ttl_no_override(self):
        """Test TTL validation with no override."""
        # Should not raise exception
        self.policy_engine.validate_ttl(
            ttl_override=None,
            channel_config=self.channel_config
        )

    def test_validate_encryption_pii_encrypted_channel(self):
        """Test encryption validation: PII content in encrypted channel."""
        encrypted_channel = ChannelConfig(
            name="secure",
            ttl_sec=3600,
            encrypt=True
        )

        # Should not raise exception
        self.policy_engine.validate_encryption(
            has_pii=True,
            channel_config=encrypted_channel
        )

    def test_validate_encryption_pii_unencrypted_channel(self):
        """Test encryption validation: PII content in unencrypted channel."""
        unencrypted_channel = ChannelConfig(
            name="public",
            ttl_sec=3600,
            encrypt=False
        )

        with pytest.raises(EncryptionRequired):
            self.policy_engine.validate_encryption(
                has_pii=True,
                channel_config=unencrypted_channel
            )

    def test_validate_encryption_no_pii(self):
        """Test encryption validation: no PII content."""
        unencrypted_channel = ChannelConfig(
            name="public",
            ttl_sec=3600,
            encrypt=False
        )

        # Should not raise exception
        self.policy_engine.validate_encryption(
            has_pii=False,
            channel_config=unencrypted_channel
        )

    def test_validate_quota_within_limit(self):
        """Test quota validation when content is within limit."""
        # Mock Redis to return current usage below limit
        self.mock_redis.get.return_value = b"500000"  # 500KB used

        # Should not raise exception
        self.policy_engine.validate_quota(
            content_size=200000,  # 200KB new content
            scope=self.scope,
            channel_config=self.channel_config  # 1MB limit
        )

    def test_validate_quota_exceeds_limit(self):
        """Test quota validation when content exceeds limit."""
        # Mock Redis to return current usage near limit
        self.mock_redis.get.return_value = b"900000"  # 900KB used

        with pytest.raises(QuotaExceeded):
            self.policy_engine.validate_quota(
                content_size=200000,  # 200KB new content (total: 1.1MB)
                scope=self.scope,
                channel_config=self.channel_config  # 1MB limit
            )

    def test_validate_quota_no_limit(self):
        """Test quota validation when channel has no quota limit."""
        no_quota_channel = ChannelConfig(
            name="unlimited",
            ttl_sec=3600,
            encrypt=False,
            quota_bytes=None
        )

        # Should not raise exception regardless of content size
        self.policy_engine.validate_quota(
            content_size=999999999,  # Very large content
            scope=self.scope,
            channel_config=no_quota_channel
        )

    def test_validate_quota_no_current_usage(self):
        """Test quota validation when no current usage exists."""
        # Mock Redis to return None (no current usage)
        self.mock_redis.get.return_value = None

        # Should not raise exception
        self.policy_engine.validate_quota(
            content_size=500000,  # 500KB new content
            scope=self.scope,
            channel_config=self.channel_config  # 1MB limit
        )

    def test_check_all_policies_pass(self):
        """Test check_all_policies when all policies pass."""
        # Mock Redis for quota check
        self.mock_redis.get.return_value = b"100000"  # Low usage

        content = "This is normal content without PII"

        # Should not raise exception
        self.policy_engine.check_all_policies(
            content=content,
            scope=self.scope,
            channel_config=self.channel_config,
            ttl_override=1800  # Within limit
        )

    def test_check_all_policies_ttl_violation(self):
        """Test check_all_policies with TTL violation."""
        content = "Normal content"

        with pytest.raises(TTLViolation):
            self.policy_engine.check_all_policies(
                content=content,
                scope=self.scope,
                channel_config=self.channel_config,
                ttl_override=7200  # Exceeds limit
            )

    def test_check_all_policies_encryption_violation(self):
        """Test check_all_policies with encryption violation."""
        # Mock Redis for quota check
        self.mock_redis.get.return_value = b"100000"

        unencrypted_channel = ChannelConfig(
            name="public",
            ttl_sec=3600,
            encrypt=False
        )

        content = "Contact me at user@example.com"  # Contains PII

        with pytest.raises(EncryptionRequired):
            self.policy_engine.check_all_policies(
                content=content,
                scope=self.scope,
                channel_config=unencrypted_channel
            )

    def test_check_all_policies_quota_violation(self):
        """Test check_all_policies with quota violation."""
        # Mock Redis to return high usage
        self.mock_redis.get.return_value = b"950000"  # 950KB used

        content = "x" * 100000  # 100KB content (total: 1.05MB)

        with pytest.raises(QuotaExceeded):
            self.policy_engine.check_all_policies(
                content=content,
                scope=self.scope,
                channel_config=self.channel_config  # 1MB limit
            )

    def test_update_quota_usage(self):
        """Test quota usage update."""
        self.policy_engine.update_quota_usage(
            scope=self.scope,
            channel_config=self.channel_config,
            content_size=50000
        )

        # Verify Redis operations
        expected_key = f"{self.scope.env}:{self.scope.agent_id}:{self.scope.user_id}:quota:{self.channel_config.name}"
        self.mock_redis.incrby.assert_called_once_with(expected_key, 50000)
        self.mock_redis.expire.assert_called_once_with(expected_key, 86400)  # 24 hours

    def test_get_quota_key(self):
        """Test quota key generation."""
        key = self.policy_engine._get_quota_key(self.scope, self.channel_config.name)
        expected = f"{self.scope.env}:{self.scope.agent_id}:{self.scope.user_id}:quota:{self.channel_config.name}"
        assert key == expected

    def test_policy_engine_without_redis(self):
        """Test PolicyEngine initialization without Redis client."""
        # Should work for basic operations
        engine = PolicyEngine()

        # TTL validation should still work
        engine.validate_ttl(1800, self.channel_config)

        # Encryption validation should still work
        engine.validate_encryption(False, self.channel_config)

        # Quota validation should skip when no Redis client
        engine.validate_quota(50000, self.scope, self.channel_config)

    def test_custom_pii_detector(self):
        """Test PolicyEngine with custom PII detector."""
        custom_detector = PIIDetector(patterns={"test_pattern": r"TEST-\d+"})
        engine = PolicyEngine(pii_detector=custom_detector)

        assert engine.pii_detector == custom_detector

    def test_bytes_content_size_calculation(self):
        """Test content size calculation for bytes input."""
        content = b"test content"
        
        # Mock Redis for quota check
        self.mock_redis.get.return_value = b"0"

        # Should not raise exception
        self.policy_engine.validate_quota(
            content_size=len(content),
            scope=self.scope,
            channel_config=self.channel_config
        )

    def test_string_content_size_calculation(self):
        """Test content size calculation for string input."""
        content = "test content with unicode: 🔒"
        content_bytes = content.encode('utf-8')
        
        # Mock Redis for quota check
        self.mock_redis.get.return_value = b"0"

        # Should not raise exception
        self.policy_engine.validate_quota(
            content_size=len(content_bytes),
            scope=self.scope,
            channel_config=self.channel_config
        )
