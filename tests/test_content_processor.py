"""
Unit tests for Content Processor module - ContentProcessorChain, PIIRedactor, ContentEnricher
"""
import pytest

from nexamem.content_processor import (
    ContentEnricher,
    ContentProcessor,
    ContentProcessorChain,
    PIIRedactor,
)


class TestContentProcessor:
    """Test suite for base ContentProcessor class."""

    def test_content_processor_interface(self):
        """Test ContentProcessor is an abstract base class."""
        # Cannot instantiate directly
        with pytest.raises(TypeError):
            ContentProcessor()

    def test_content_processor_subclass(self):
        """Test creating a valid ContentProcessor subclass."""
        class TestProcessor(ContentProcessor):
            def process(self, content: str, metadata: dict = None) -> tuple:
                return content.upper(), metadata or {}

        processor = TestProcessor()
        result_content, result_metadata = processor.process("hello")
        assert result_content == "HELLO"
        assert isinstance(result_metadata, dict)


class TestPIIRedactor:
    """Test suite for PIIRedactor class."""

    def test_redact_email(self):
        """Test email redaction."""
        redactor = PIIRedactor()
        content = "Contact me at john@example.com for more info"

        processed_content, metadata = redactor.process(content)

        assert "john@example.com" not in processed_content
        assert "[EMAIL_REDACTED]" in processed_content
        assert metadata["redactions"]["email"] == 1
        assert metadata["has_redactions"] is True

    def test_redact_phone(self):
        """Test phone number redaction."""
        redactor = PIIRedactor()
        content = "Call me at 555-123-4567 tomorrow"

        processed_content, metadata = redactor.process(content)

        assert "555-123-4567" not in processed_content
        assert "[PHONE_REDACTED]" in processed_content
        assert metadata["redactions"]["phone"] == 1

    def test_redact_ssn(self):
        """Test SSN redaction."""
        redactor = PIIRedactor()
        content = "My SSN is 123-45-6789"

        processed_content, metadata = redactor.process(content)

        assert "123-45-6789" not in processed_content
        assert "[SSN_REDACTED]" in processed_content
        assert metadata["redactions"]["ssn"] == 1

    def test_redact_credit_card(self):
        """Test credit card redaction."""
        redactor = PIIRedactor()
        content = "Card number: 1234-5678-9012-3456"

        processed_content, metadata = redactor.process(content)

        assert "1234-5678-9012-3456" not in processed_content
        assert "[CREDIT_CARD_REDACTED]" in processed_content
        assert metadata["redactions"]["credit_card"] == 1

    def test_redact_multiple_pii_types(self):
        """Test redaction of multiple PII types."""
        redactor = PIIRedactor()
        content = "Email: test@example.com, Phone: 555-123-4567, SSN: 123-45-6789"

        processed_content, metadata = redactor.process(content)

        assert "test@example.com" not in processed_content
        assert "555-123-4567" not in processed_content
        assert "123-45-6789" not in processed_content
        assert "[EMAIL_REDACTED]" in processed_content
        assert "[PHONE_REDACTED]" in processed_content
        assert "[SSN_REDACTED]" in processed_content

        assert metadata["redactions"]["email"] == 1
        assert metadata["redactions"]["phone"] == 1
        assert metadata["redactions"]["ssn"] == 1
        assert metadata["has_redactions"] is True

    def test_redact_multiple_same_type(self):
        """Test redaction of multiple instances of same PII type."""
        redactor = PIIRedactor()
        content = "Emails: test1@example.com and test2@example.com"

        processed_content, metadata = redactor.process(content)

        assert "test1@example.com" not in processed_content
        assert "test2@example.com" not in processed_content
        assert processed_content.count("[EMAIL_REDACTED]") == 2
        assert metadata["redactions"]["email"] == 2

    def test_no_pii_content(self):
        """Test processing content without PII."""
        redactor = PIIRedactor()
        content = "This is just normal text without any sensitive information"

        processed_content, metadata = redactor.process(content)

        assert processed_content == content  # No changes
        assert metadata["has_redactions"] is False
        assert sum(metadata["redactions"].values()) == 0

    def test_custom_redaction_patterns(self):
        """Test PIIRedactor with custom patterns."""
        custom_patterns = {
            "custom_id": r"ID-\d{6}",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        }
        custom_replacements = {
            "custom_id": "[CUSTOM_ID_REDACTED]",
            "email": "[EMAIL_REDACTED]"
        }

        redactor = PIIRedactor(patterns=custom_patterns, replacements=custom_replacements)
        content = "My ID is ID-123456 and email is test@example.com"

        processed_content, metadata = redactor.process(content)

        assert "ID-123456" not in processed_content
        assert "[CUSTOM_ID_REDACTED]" in processed_content
        assert metadata["redactions"]["custom_id"] == 1

    def test_preserve_existing_metadata(self):
        """Test that existing metadata is preserved and extended."""
        redactor = PIIRedactor()
        content = "Email me at test@example.com"
        existing_metadata = {"source": "user_input", "timestamp": "2024-01-01"}

        processed_content, metadata = redactor.process(content, existing_metadata)

        # Original metadata preserved
        assert metadata["source"] == "user_input"
        assert metadata["timestamp"] == "2024-01-01"

        # New metadata added
        assert metadata["has_redactions"] is True
        assert metadata["redactions"]["email"] == 1

    def test_empty_content(self):
        """Test processing empty content."""
        redactor = PIIRedactor()
        processed_content, metadata = redactor.process("")

        assert processed_content == ""
        assert metadata["has_redactions"] is False

    def test_none_content(self):
        """Test processing None content."""
        redactor = PIIRedactor()

        with pytest.raises(TypeError):
            redactor.process(None)


class TestContentEnricher:
    """Test suite for ContentEnricher class."""

    def test_basic_enrichment(self):
        """Test basic content enrichment."""
        enricher = ContentEnricher()
        content = "This is a test message with some words."

        processed_content, metadata = enricher.process(content)

        assert processed_content == content  # Content unchanged
        assert metadata["content_length"] == len(content)
        assert metadata["word_count"] == 8
        assert metadata["char_count"] == len(content)

    def test_enrichment_with_existing_metadata(self):
        """Test enrichment preserves existing metadata."""
        enricher = ContentEnricher()
        content = "Hello world"
        existing_metadata = {"source": "api", "user_id": "123"}

        processed_content, metadata = enricher.process(content, existing_metadata)

        # Original metadata preserved
        assert metadata["source"] == "api"
        assert metadata["user_id"] == "123"

        # Enrichment added
        assert metadata["content_length"] == 11
        assert metadata["word_count"] == 2

    def test_empty_content_enrichment(self):
        """Test enrichment of empty content."""
        enricher = ContentEnricher()
        processed_content, metadata = enricher.process("")

        assert processed_content == ""
        assert metadata["content_length"] == 0
        assert metadata["word_count"] == 0
        assert metadata["char_count"] == 0

    def test_whitespace_content_enrichment(self):
        """Test enrichment of whitespace-only content."""
        enricher = ContentEnricher()
        content = "   \n\t  "

        processed_content, metadata = enricher.process(content)

        assert processed_content == content
        assert metadata["content_length"] == len(content)
        assert metadata["word_count"] == 0  # No actual words

    def test_unicode_content_enrichment(self):
        """Test enrichment of Unicode content."""
        enricher = ContentEnricher()
        content = "Hello 世界! This is test 🔒"

        processed_content, metadata = enricher.process(content)

        assert processed_content == content
        assert metadata["content_length"] == len(content)
        assert metadata["word_count"] == 5  # Hello, 世界!, This, is, test
        assert metadata["char_count"] == len(content)

    def test_multiline_content_enrichment(self):
        """Test enrichment of multiline content."""
        enricher = ContentEnricher()
        content = "Line one\nLine two\nLine three"

        processed_content, metadata = enricher.process(content)

        assert processed_content == content
        assert metadata["word_count"] == 6  # Line, one, Line, two, Line, three

    def test_punctuation_handling(self):
        """Test word counting with punctuation."""
        enricher = ContentEnricher()
        content = "Hello, world! How are you? I'm fine."

        processed_content, metadata = enricher.process(content)

        assert metadata["word_count"] == 7  # Hello, world, How, are, you, I'm, fine


class TestContentProcessorChain:
    """Test suite for ContentProcessorChain class."""

    def test_empty_chain(self):
        """Test empty processor chain."""
        chain = ContentProcessorChain([])
        content = "Test content"

        processed_content, metadata = chain.process(content)

        assert processed_content == content
        assert metadata == {}

    def test_single_processor_chain(self):
        """Test chain with single processor."""
        enricher = ContentEnricher()
        chain = ContentProcessorChain([enricher])
        content = "Hello world"

        processed_content, metadata = chain.process(content)

        assert processed_content == content
        assert metadata["word_count"] == 2

    def test_multiple_processor_chain(self):
        """Test chain with multiple processors."""
        redactor = PIIRedactor()
        enricher = ContentEnricher()
        chain = ContentProcessorChain([redactor, enricher])

        content = "Contact me at test@example.com for info"

        processed_content, metadata = chain.process(content)

        # Content should be redacted
        assert "test@example.com" not in processed_content
        assert "[EMAIL_REDACTED]" in processed_content

        # Should have both redaction and enrichment metadata
        assert metadata["has_redactions"] is True
        assert metadata["redactions"]["email"] == 1
        assert "word_count" in metadata
        assert "content_length" in metadata

    def test_chain_metadata_accumulation(self):
        """Test that metadata accumulates through the chain."""
        class MetadataProcessor1(ContentProcessor):
            def process(self, content: str, metadata: dict = None) -> tuple:
                meta = metadata or {}
                meta["processor1"] = "ran"
                return content, meta

        class MetadataProcessor2(ContentProcessor):
            def process(self, content: str, metadata: dict = None) -> tuple:
                meta = metadata or {}
                meta["processor2"] = "ran"
                return content, meta

        chain = ContentProcessorChain([MetadataProcessor1(), MetadataProcessor2()])
        content = "test"

        processed_content, metadata = chain.process(content)

        assert metadata["processor1"] == "ran"
        assert metadata["processor2"] == "ran"

    def test_chain_content_transformation(self):
        """Test that content transformations flow through the chain."""
        class UppercaseProcessor(ContentProcessor):
            def process(self, content: str, metadata: dict = None) -> tuple:
                return content.upper(), metadata or {}

        class PrefixProcessor(ContentProcessor):
            def process(self, content: str, metadata: dict = None) -> tuple:
                return f"PREFIX: {content}", metadata or {}

        chain = ContentProcessorChain([UppercaseProcessor(), PrefixProcessor()])
        content = "hello"

        processed_content, metadata = chain.process(content)

        assert processed_content == "PREFIX: HELLO"

    def test_chain_with_failing_processor(self):
        """Test chain behavior when a processor raises an exception."""
        class FailingProcessor(ContentProcessor):
            def process(self, content: str, metadata: dict = None) -> tuple:
                raise ValueError("Processor failed")

        enricher = ContentEnricher()
        chain = ContentProcessorChain([enricher, FailingProcessor()])

        content = "test content"

        with pytest.raises(ValueError, match="Processor failed"):
            chain.process(content)

    def test_chain_with_initial_metadata(self):
        """Test chain processing with initial metadata."""
        enricher = ContentEnricher()
        chain = ContentProcessorChain([enricher])

        content = "hello"
        initial_metadata = {"source": "test", "timestamp": "2024-01-01"}

        processed_content, metadata = chain.process(content, initial_metadata)

        # Original metadata preserved
        assert metadata["source"] == "test"
        assert metadata["timestamp"] == "2024-01-01"

        # Enrichment added
        assert metadata["word_count"] == 1

    def test_chain_processor_order_matters(self):
        """Test that processor order affects the final result."""
        class AddAProcessor(ContentProcessor):
            def process(self, content: str, metadata: dict = None) -> tuple:
                return content + "A", metadata or {}

        class AddBProcessor(ContentProcessor):
            def process(self, content: str, metadata: dict = None) -> tuple:
                return content + "B", metadata or {}

        # Order 1: A then B
        chain1 = ContentProcessorChain([AddAProcessor(), AddBProcessor()])
        result1, _ = chain1.process("X")

        # Order 2: B then A
        chain2 = ContentProcessorChain([AddBProcessor(), AddAProcessor()])
        result2, _ = chain2.process("X")

        assert result1 == "XAB"
        assert result2 == "XBA"
        assert result1 != result2

    def test_integration_redaction_and_enrichment(self):
        """Test integration of redaction and enrichment processors."""
        redactor = PIIRedactor()
        enricher = ContentEnricher()
        chain = ContentProcessorChain([redactor, enricher])

        content = "My email is user@example.com and phone is 555-123-4567"

        processed_content, metadata = chain.process(content)

        # Verify redaction occurred
        assert "user@example.com" not in processed_content
        assert "555-123-4567" not in processed_content
        assert "[EMAIL_REDACTED]" in processed_content
        assert "[PHONE_REDACTED]" in processed_content

        # Verify enrichment of redacted content
        expected_length = len(processed_content)
        assert metadata["content_length"] == expected_length
        assert metadata["word_count"] > 0

        # Verify redaction metadata
        assert metadata["has_redactions"] is True
        assert metadata["redactions"]["email"] == 1
        assert metadata["redactions"]["phone"] == 1
