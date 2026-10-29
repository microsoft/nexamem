"""Optional telemetry, context continuity, and privacy checks."""

import asyncio
import sys

import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from nexamem import AIMemory, AIMemoryConfig, AsyncAIMemory, MemoryScope, StorageConfig, telemetry


@pytest.fixture
def exported_telemetry(monkeypatch):
    exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))
    reader = InMemoryMetricReader()
    meter_provider = MeterProvider(metric_readers=[reader])
    monkeypatch.setattr(trace, "get_tracer", tracer_provider.get_tracer)
    monkeypatch.setattr(metrics, "get_meter", meter_provider.get_meter)
    telemetry._instruments.cache_clear()
    try:
        yield tracer_provider.get_tracer("application"), exporter, reader
    finally:
        telemetry._instruments.cache_clear()
        tracer_provider.shutdown()
        meter_provider.shutdown()


async def test_operations_without_opentelemetry(monkeypatch):
    monkeypatch.setitem(sys.modules, "opentelemetry", None)
    telemetry._instruments.cache_clear()

    @telemetry.trace_operation("probe")
    def sync_operation(value):
        return value

    @telemetry.trace_async_operation("probe")
    async def async_operation(value):
        return value

    failure = RuntimeError("original error")

    @telemetry.trace_operation("failure")
    def failing_operation():
        raise failure

    try:
        assert sync_operation("sync") == "sync"
        assert await async_operation("async") == "async"
        with pytest.raises(RuntimeError) as caught:
            failing_operation()
        assert caught.value is failure
    finally:
        telemetry._instruments.cache_clear()


@pytest.mark.parametrize("async_mode", [False, True])
async def test_public_operations_and_metrics(exported_telemetry, async_mode):
    tracer, exporter, reader = exported_telemetry
    config = AIMemoryConfig(default_scope="private-scope", storage=StorageConfig.memory())
    memory = AsyncAIMemory(config) if async_mode else AIMemory(config)
    scope = MemoryScope(agent_id="private-agent", user_id="private-user")
    memory.register_channel("notes", ttl_sec=60)

    async def invoke(name, *args, **kwargs):
        result = getattr(memory, name)(*args, **kwargs)
        return await result if async_mode else result

    with tracer.start_as_current_span("request") as parent:
        memory_id = await invoke(
            "store", "private-content", memory_id="private-id", metadata={"secret": "private-value"}
        )
        assert (await invoke("retrieve", memory_id))["content"] == "private-content"
        assert memory_id in await invoke("list")
        assert memory_id in await invoke("search", "private")
        assert await invoke("get_audit_log")
        assert (await invoke("get_stats"))["total_memories"] == 1
        assert await invoke("delete", memory_id)
        await invoke("store", "another secret")
        assert await invoke("clear_scope") == 1
        await invoke("write", scope, "notes", "private-channel-content")
        assert (await invoke("read", scope, "notes"))[0] == ["private-channel-content"]

    spans = exporter.get_finished_spans()
    operations = [span for span in spans if span.instrumentation_scope.name == "nexamem"]
    assert {span.name for span in operations} == {
        f"nexamem.{name}"
        for name in (
            "store",
            "retrieve",
            "delete",
            "list",
            "search",
            "get_audit_log",
            "get_stats",
            "clear_scope",
            "write",
            "read",
        )
    }
    assert all(span.context.trace_id == parent.get_span_context().trace_id for span in operations)
    assert operations[0].parent.span_id == parent.get_span_context().span_id
    assert "private" not in repr([(span.attributes, span.events) for span in spans])
    data = reader.get_metrics_data()
    emitted = {
        metric.name: metric
        for resource in data.resource_metrics
        for instrumentation in resource.scope_metrics
        for metric in instrumentation.metrics
    }
    counts = emitted["nexamem.operations"].data.data_points
    durations = emitted["nexamem.operation.duration"].data.data_points
    assert sum(point.value for point in counts) == len(operations)
    assert sum(point.count for point in durations) == len(operations)
    assert all(point.attributes["nexamem.outcome"] == "success" for point in counts)
    assert all(point.sum >= 0 for point in durations)
    assert "private" not in repr([point.attributes for point in counts])


@pytest.mark.parametrize("async_mode", [False, True])
async def test_failures_preserve_exception_without_exporting_message(
    exported_telemetry, monkeypatch, async_mode
):
    tracer, exporter, reader = exported_telemetry
    config = AIMemoryConfig(storage=StorageConfig.memory())
    memory = AsyncAIMemory(config) if async_mode else AIMemory(config)
    failure = RuntimeError("private password or memory content")

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(memory._storage, "store_memory", fail)
    with tracer.start_as_current_span("request"):
        with pytest.raises(RuntimeError) as caught:
            if async_mode:
                await memory.store("private content")
            else:
                memory.store("private content")
    assert caught.value is failure
    span = exporter.get_finished_spans()[0]
    assert span.status.status_code == StatusCode.ERROR
    assert span.status.description is None
    assert span.attributes["error.type"] == "RuntimeError"
    assert not span.events
    assert "private" not in repr(span.attributes)
    data = reader.get_metrics_data()
    counts = data.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points
    assert counts[0].attributes["nexamem.outcome"] == "error"


async def test_concurrent_async_contexts_stay_separate(exported_telemetry):
    tracer, exporter, _ = exported_telemetry
    memory = AsyncAIMemory(AIMemoryConfig(storage=StorageConfig.memory()))
    parents = {}

    async def request(name):
        with tracer.start_as_current_span(name) as parent:
            parents[name] = parent.get_span_context()
            await asyncio.sleep(0)
            await memory.store("private content")
            assert trace.get_current_span().get_span_context() == parents[name]

    await asyncio.gather(request("first"), request("second"))
    operations = [span for span in exporter.get_finished_spans() if span.name == "nexamem.store"]
    assert {span.parent.span_id for span in operations} == {
        context.span_id for context in parents.values()
    }
    assert {span.context.trace_id for span in operations} == {
        context.trace_id for context in parents.values()
    }


async def test_async_cancellation_is_propagated(exported_telemetry, monkeypatch):
    _, exporter, _ = exported_telemetry
    memory = AsyncAIMemory(AIMemoryConfig(storage=StorageConfig.memory()))
    entered = asyncio.Event()
    blocker = asyncio.Event()

    async def wait(*args, **kwargs):
        entered.set()
        await blocker.wait()

    monkeypatch.setattr(memory._storage, "store_memory", wait)
    task = asyncio.create_task(memory.store("private content"))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    span = exporter.get_finished_spans()[0]
    assert span.attributes["error.type"] == "CancelledError"
    assert span.status.status_code == StatusCode.ERROR
    assert not span.events
