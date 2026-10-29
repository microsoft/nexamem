"""Optional OpenTelemetry instrumentation; providers and exporters belong to the host app."""

from collections.abc import Callable, Coroutine, Iterator
from contextlib import contextmanager
from functools import lru_cache, wraps
from time import perf_counter
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

if TYPE_CHECKING:
    from opentelemetry.metrics import Counter, Histogram
    from opentelemetry.trace import Tracer

Parameters = ParamSpec("Parameters")
Result = TypeVar("Result")
INSTRUMENTATION_SCOPE = "nexamem"


@lru_cache(maxsize=1)
def _instruments() -> tuple["Tracer", "Counter", "Histogram"] | None:
    try:
        from opentelemetry import metrics, trace
    except ImportError:
        return None

    meter = metrics.get_meter(INSTRUMENTATION_SCOPE)
    return (
        trace.get_tracer(INSTRUMENTATION_SCOPE),
        meter.create_counter("nexamem.operations", unit="{operation}"),
        meter.create_histogram("nexamem.operation.duration", unit="s"),
    )


@contextmanager
def _operation(name: str) -> Iterator[None]:
    instruments = _instruments()
    if instruments is None:
        yield
        return

    from opentelemetry.trace import StatusCode

    tracer, counter, duration = instruments
    attributes = {"nexamem.operation": name}
    started = perf_counter()
    with tracer.start_as_current_span(
        f"nexamem.{name}",
        attributes=attributes,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        outcome = "success"
        try:
            yield
        except BaseException as error:
            outcome = "error"
            span.set_status(StatusCode.ERROR)
            span.set_attribute("error.type", type(error).__name__)
            raise
        finally:
            labels = {**attributes, "nexamem.outcome": outcome}
            counter.add(1, labels)
            duration.record(perf_counter() - started, labels)


def trace_operation(
    name: str,
) -> Callable[[Callable[Parameters, Result]], Callable[Parameters, Result]]:
    """Trace a synchronous operation without recording its arguments or result."""

    def decorate(function: Callable[Parameters, Result]) -> Callable[Parameters, Result]:
        @wraps(function)
        def wrapped(*args: Parameters.args, **kwargs: Parameters.kwargs) -> Result:
            with _operation(name):
                return function(*args, **kwargs)

        return wrapped

    return decorate


def trace_async_operation(
    name: str,
) -> Callable[
    [Callable[Parameters, Coroutine[Any, Any, Result]]],
    Callable[Parameters, Coroutine[Any, Any, Result]],
]:
    """Trace an awaited operation while retaining the caller's active context."""

    def decorate(
        function: Callable[Parameters, Coroutine[Any, Any, Result]],
    ) -> Callable[Parameters, Coroutine[Any, Any, Result]]:
        @wraps(function)
        async def wrapped(*args: Parameters.args, **kwargs: Parameters.kwargs) -> Result:
            with _operation(name):
                return await function(*args, **kwargs)

        return wrapped

    return decorate
