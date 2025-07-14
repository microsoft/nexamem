"""
Metrics collection for AIMemory operations.
"""
import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Basic metrics collector for AIMemory operations.
    Provides Prometheus-style counters and histograms.
    """
    
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._lock = threading.Lock()
        self.enabled = True
    
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        if not self.enabled:
            return
        
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += 1
    
    def record_duration(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a duration in a histogram."""
        if not self.enabled:
            return
        
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(duration)
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """Get current counter value."""
        key = self._make_key(name, labels)
        with self._lock:
            return self._counters.get(key, 0)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(name, labels)
        with self._lock:
            values = list(self._histograms.get(key, []))
        
        if not values:
            return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
        
        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values)
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self._lock:
            metrics = {
                "counters": dict(self._counters),
                "histograms": {}
            }
            
            for name in self._histograms:
                metrics["histograms"][name] = self.get_histogram_stats("", {"key": name})
        
        return metrics
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
    
    def disable(self) -> None:
        """Disable metrics collection."""
        self.enabled = False
    
    def enable(self) -> None:
        """Enable metrics collection."""
        self.enabled = True
    
    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """Create a metric key from name and labels."""
        if not labels:
            return name
        
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class MetricsTimer:
    """Context manager for timing operations."""
    
    def __init__(self, metrics: MetricsCollector, name: str, labels: Optional[Dict[str, str]] = None):
        self.metrics = metrics
        self.name = name
        self.labels = labels
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.metrics.record_duration(self.name, duration, self.labels)


# Global metrics instance
_global_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    return _global_metrics


def increment_counter(name: str, labels: Optional[Dict[str, str]] = None) -> None:
    """Increment a global counter."""
    _global_metrics.increment_counter(name, labels)


def record_duration(name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
    """Record a duration in a global histogram."""
    _global_metrics.record_duration(name, duration, labels)


def timer(name: str, labels: Optional[Dict[str, str]] = None) -> MetricsTimer:
    """Create a timer context manager."""
    return MetricsTimer(_global_metrics, name, labels)


# Standard AIMemory metrics
def record_write_operation(channel: str, success: bool = True, duration: Optional[float] = None) -> None:
    """Record a write operation."""
    labels = {"channel": channel, "status": "success" if success else "error"}
    increment_counter("ai_memory_write_total", labels)
    
    if duration is not None:
        record_duration("ai_memory_write_duration_seconds", duration, {"channel": channel})


def record_read_operation(channel: str, success: bool = True, duration: Optional[float] = None) -> None:
    """Record a read operation."""
    labels = {"channel": channel, "status": "success" if success else "error"}
    increment_counter("ai_memory_read_total", labels)
    
    if duration is not None:
        record_duration("ai_memory_read_duration_seconds", duration, {"channel": channel})


def record_checkpoint_operation(operation: str, success: bool = True, duration: Optional[float] = None) -> None:
    """Record a checkpoint operation."""
    labels = {"operation": operation, "status": "success" if success else "error"}
    increment_counter("ai_memory_checkpoint_total", labels)
    
    if duration is not None:
        record_duration("ai_memory_checkpoint_duration_seconds", duration, {"operation": operation})
