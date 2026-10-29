"""Deterministic policy and content-processing unit tests."""

import pytest

from nexamem.channels import ChannelConfig
from nexamem.content_processor import (
    ContentEnricher,
    ContentProcessorChain,
    PIIRedactor,
    create_default_chain,
)
from nexamem.policy import (
    EncryptionRequired,
    PIIDetector,
    PolicyEngine,
    QuotaExceeded,
    QuotaTracker,
    TTLViolation,
)


@pytest.mark.parametrize(
    "kind,content",
    [
        ("email", "person@example.com"),
        ("phone", "212-555-1234"),
        ("ssn", "123-45-6789"),
        ("credit_card", "4111 1111 1111 1111"),
    ],
)
def test_pii_detection_and_redaction(kind: str, content: str) -> None:
    detector = PIIDetector()
    assert detector.has_pii(content)
    assert detector.detect_pii(content)[kind]
    original = {"source": "test"}
    redacted, metadata = PIIRedactor().process(content, original)
    assert content not in redacted
    assert f"[REDACTED_{kind.upper()}]" in redacted
    assert metadata["pii_redacted"]
    assert kind in metadata["pii_detected"]
    assert original == {"source": "test"}


def test_content_chains(caplog: pytest.LogCaptureFixture) -> None:
    assert not PIIDetector().has_pii("ordinary words")
    assert PIIDetector({"custom": "secret"}).has_pii("SECRET")
    assert ContentProcessorChain().process("words", {"source": "test"}) == (
        "words",
        {"source": "test"},
    )
    assert ContentProcessorChain().process("words") == ("words", {})
    content, metadata = create_default_chain().process("two words")
    assert content == "two words"
    assert metadata == {"content_length": 9, "word_count": 2}
    content, metadata = create_default_chain(auto_pii=True).process("person@example.com")
    assert content == "[REDACTED_EMAIL]"
    assert metadata["word_count"] == 1

    class BrokenProcessor:
        def process(self, content: str, metadata: dict) -> tuple:
            raise RuntimeError("processor unavailable")

    chain = ContentProcessorChain([BrokenProcessor(), ContentEnricher()])
    assert chain.process("content")[1]["content_length"] == 7
    assert "processor unavailable" in caplog.text


def test_policy_validation_and_quota(monkeypatch: pytest.MonkeyPatch) -> None:
    scope = {"agent_id": "agent", "user_id": "user"}
    channel = ChannelConfig(name="working", ttl_sec=120, encrypt=True, quota_bytes=10)
    engine = PolicyEngine()
    result = engine.validate_write(b"hello", channel, scope, pii=True, ttl_override=60)
    assert result == {
        "has_pii": True,
        "detected_pii": {},
        "content_bytes": 5,
        "effective_ttl": 60,
        "requires_encryption": True,
    }
    engine.post_write_update(5, scope, "working")
    engine.validate_write("hello", channel, scope)
    with pytest.raises(QuotaExceeded):
        engine.validate_write("sixsix", channel, scope)
    with pytest.raises(TTLViolation):
        engine.validate_write("safe", channel, scope, ttl_override=121)
    plain = ChannelConfig(name="plain", ttl_sec=120)
    with pytest.raises(EncryptionRequired):
        engine.validate_write("safe", plain, scope, pii=True)
    with pytest.raises(EncryptionRequired):
        engine.validate_write("person@example.com", plain, scope, auto_pii=True)
    result = engine.validate_write("person@example.com", plain, scope)
    assert not result["has_pii"]
    assert result["detected_pii"]["email"]
    assert result["effective_ttl"] == 120
    monkeypatch.setattr(engine.quota_tracker, "_get_current_date", lambda: "tomorrow")
    assert engine.validate_write("sixsix", channel, scope)["content_bytes"] == 6


def test_quota_rollover(monkeypatch: pytest.MonkeyPatch) -> None:
    tracker = QuotaTracker()
    tracker.check_quota("agent", "user", "channel", 100, None)
    assert tracker._quotas == {}
    tracker.update_quota("agent", "user", "channel", 4)
    with pytest.raises(QuotaExceeded):
        tracker.check_quota("agent", "user", "channel", 2, 5)
    monkeypatch.setattr(tracker, "_get_current_date", lambda: "next-day")
    tracker.update_quota("agent", "user", "channel", 2)
    tracker.check_quota("agent", "user", "channel", 3, 5)
    assert tracker._quotas["agent:user:channel"]["bytes_used"] == 2
