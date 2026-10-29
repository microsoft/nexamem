"""Local metrics and Redis stream auditing contracts."""

import json
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import fakeredis
import pytest

from nexamem import metrics
from nexamem.audit import AsyncAuditSink, AuditSink


def test_metrics_snapshot_does_not_deadlock() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from nexamem.metrics import MetricsCollector; "
            "collector=MetricsCollector(); collector.record_duration('operation', 2); "
            "assert collector.get_all_metrics()['histograms']['operation']['sum'] == 2",
        ],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr


def test_metrics_counters_histograms_and_timers() -> None:
    collector = metrics.MetricsCollector()
    labels = {"user": "test", "channel": "working"}
    collector.increment_counter("writes", labels)
    assert collector.get_counter("writes", dict(reversed(list(labels.items())))) == 1
    assert collector.get_counter("missing") == 0
    assert collector.get_histogram_stats("missing")["count"] == 0
    collector.record_duration("duration", 1)
    collector.record_duration("duration", 3)
    assert collector.get_histogram_stats("duration") == {
        "count": 2,
        "sum": 4,
        "avg": 2,
        "min": 1,
        "max": 3,
    }
    collector.disable()
    collector.increment_counter("disabled")
    collector.record_duration("disabled", 1)
    assert collector.get_counter("disabled") == 0
    assert collector.get_histogram_stats("disabled")["count"] == 0
    collector.enable()
    with patch("nexamem.metrics.time.time", side_effect=[10, 12]):
        with metrics.MetricsTimer(collector, "timed"):
            pass
    assert collector.get_histogram_stats("timed")["sum"] == 2
    collector.reset()
    assert collector.get_all_metrics() == {"counters": {}, "histograms": {}}


def test_global_operation_metrics() -> None:
    collector = metrics.get_metrics()
    collector.reset()
    try:
        metrics.record_write_operation("working", duration=0.1)
        metrics.record_read_operation("working", False, 0.2)
        metrics.record_checkpoint_operation("save", duration=0.3)
        with metrics.timer("global"):
            pass
        assert (
            collector.get_counter(
                "ai_memory_write_total", {"channel": "working", "status": "success"}
            )
            == 1
        )
        assert (
            collector.get_counter("ai_memory_read_total", {"channel": "working", "status": "error"})
            == 1
        )
        assert (
            collector.get_counter(
                "ai_memory_checkpoint_total", {"operation": "save", "status": "success"}
            )
            == 1
        )
        assert collector.get_histogram_stats("global")["count"] == 1
    finally:
        collector.reset()


@pytest.mark.parametrize("decoded", [False, True])
def test_audit_stream_round_trip(decoded: bool) -> None:
    client = fakeredis.FakeRedis(decode_responses=decoded)
    sink = AuditSink(SimpleNamespace(client=client))
    sink.log_operation("store", {"agent_id": "agent"}, "working", {"memory_id": "one"})
    assert client.ttl(sink.stream_name) > 0
    records = sink.get_audit_records(count=1)
    assert len(records) == 1
    assert records[0]["operation"] == "store"
    assert records[0]["scope"] == {"agent_id": "agent"}
    assert records[0]["metadata"]["memory_id"] == "one"
    assert "stream_id" in records[0]
    sink.disable()
    sink.log_operation("ignored", {})
    assert client.xlen(sink.stream_name) == 1
    sink.enable()
    sink.log_operation("read", {})
    assert client.xlen(sink.stream_name) == 2
    client.close()


def test_audit_failures_and_malformed_records(caplog: pytest.LogCaptureFixture) -> None:
    client = Mock()
    sink = AuditSink(SimpleNamespace(client=client))
    client.xrange.return_value = [
        (None, None),
        (b"1-0", {b"data": json.dumps({"operation": "read"}).encode()}),
        (b"2-0", {b"data": b"invalid"}),
        (b"3-0", {}),
        (b"4-0", {b"data": b"\xff"}),
    ]
    assert sink.get_audit_records()[0]["operation"] == "read"
    assert "Failed to parse" in caplog.text
    client.xrange.side_effect = RuntimeError("unavailable")
    assert sink.get_audit_records() == []
    client.xadd.side_effect = RuntimeError("unavailable")
    sink.log_operation("read", {})
    assert "Failed to add" in caplog.text
    with patch.object(sink, "_add_to_stream", side_effect=RuntimeError("outer failure")):
        sink.log_operation("read", {})
    assert "outer failure" in caplog.text


async def test_async_audit_sink(caplog: pytest.LogCaptureFixture) -> None:
    client = SimpleNamespace(xadd=AsyncMock(), expire=AsyncMock())
    sink = AsyncAuditSink(SimpleNamespace(client=client))
    await sink.log_operation("write", {"user_id": "test"}, "working")
    record = json.loads(client.xadd.call_args.args[1]["data"])
    assert record["scope"]["user_id"] == "test"
    client.expire.assert_awaited_once_with(sink.stream_name, 365 * 86400)
    sink.disable()
    await sink.log_operation("ignored", {})
    assert client.xadd.await_count == 1
    sink.enable()
    client.xadd.side_effect = RuntimeError("unavailable")
    await sink.log_operation("read", {})
    assert "Failed to add" in caplog.text
    with patch.object(sink, "_add_to_stream", side_effect=RuntimeError("outer failure")):
        await sink.log_operation("read", {})
    assert "outer failure" in caplog.text
