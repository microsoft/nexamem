"""
Comprehensive unit tests for metrics module.
Tests Prometheus-style metrics collection for AIMemory operations.
"""
import threading
import time

import pytest

from nexamem import metrics
from nexamem.metrics import MetricsCollector


class TestMetricsCollector:
    """Test metrics collection functionality."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset global metrics before each test."""
        metrics.reset_metrics()
        yield
        metrics.reset_metrics()

    def test_metrics_collector_initialization(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector()

        assert collector.enabled is True
        assert isinstance(collector._counters, dict)
        assert isinstance(collector._histograms, dict)
        assert isinstance(collector._lock, type(threading.Lock()))

    def test_metrics_collector_disabled(self):
        """Test metrics collector when disabled."""
        collector = MetricsCollector(enabled=False)

        collector.increment_counter("test_counter", {"status": "success"})
        collector.record_histogram("test_histogram", 1.5, {"operation": "read"})

        # Should not record anything when disabled
        assert len(collector._counters) == 0
        assert len(collector._histograms) == 0

    def test_increment_counter_basic(self):
        """Test basic counter increment functionality."""
        collector = MetricsCollector()

        collector.increment_counter("ai_memory_write_total", {"channel": "working", "status": "success"})
        collector.increment_counter("ai_memory_write_total", {"channel": "working", "status": "success"})
        collector.increment_counter("ai_memory_write_total", {"channel": "routing", "status": "error"})

        counters = collector.get_counters()

        # Should have two different counter combinations
        assert len(counters) == 2

        # Check specific counts
        working_success_key = "ai_memory_write_total{channel='working',status='success'}"
        routing_error_key = "ai_memory_write_total{channel='routing',status='error'}"

        assert counters[working_success_key] == 2
        assert counters[routing_error_key] == 1

    def test_increment_counter_no_labels(self):
        """Test counter increment without labels."""
        collector = MetricsCollector()

        collector.increment_counter("simple_counter")
        collector.increment_counter("simple_counter")

        counters = collector.get_counters()
        assert counters["simple_counter"] == 2

    def test_increment_counter_empty_labels(self):
        """Test counter increment with empty labels."""
        collector = MetricsCollector()

        collector.increment_counter("test_counter", {})

        counters = collector.get_counters()
        assert counters["test_counter"] == 1

    def test_record_histogram_basic(self):
        """Test basic histogram recording functionality."""
        collector = MetricsCollector()

        collector.record_histogram("ai_memory_read_duration", 0.5, {"channel": "working"})
        collector.record_histogram("ai_memory_read_duration", 1.2, {"channel": "working"})
        collector.record_histogram("ai_memory_read_duration", 0.8, {"channel": "routing"})

        histograms = collector.get_histograms()

        # Should have two different histogram combinations
        assert len(histograms) == 2

        working_key = "ai_memory_read_duration{channel='working'}"
        routing_key = "ai_memory_read_duration{channel='routing'}"

        assert working_key in histograms
        assert routing_key in histograms

        # Check histogram data
        working_data = histograms[working_key]
        assert working_data["count"] == 2
        assert working_data["sum"] == 1.7  # 0.5 + 1.2
        assert working_data["min"] == 0.5
        assert working_data["max"] == 1.2

        routing_data = histograms[routing_key]
        assert routing_data["count"] == 1
        assert routing_data["sum"] == 0.8

    def test_record_histogram_no_labels(self):
        """Test histogram recording without labels."""
        collector = MetricsCollector()

        collector.record_histogram("simple_histogram", 2.5)
        collector.record_histogram("simple_histogram", 1.5)

        histograms = collector.get_histograms()
        data = histograms["simple_histogram"]

        assert data["count"] == 2
        assert data["sum"] == 4.0
        assert data["min"] == 1.5
        assert data["max"] == 2.5
        assert data["avg"] == 2.0

    def test_format_labels(self):
        """Test label formatting functionality."""
        collector = MetricsCollector()

        # Test with multiple labels
        labels = {"channel": "working", "status": "success", "env": "prod"}
        formatted = collector._format_labels(labels)
        expected = "channel='working',env='prod',status='success'"  # Sorted by key
        assert formatted == expected

        # Test with single label
        labels = {"status": "error"}
        formatted = collector._format_labels(labels)
        assert formatted == "status='error'"

        # Test with empty labels
        formatted = collector._format_labels({})
        assert formatted == ""

        # Test with None
        formatted = collector._format_labels(None)
        assert formatted == ""

    def test_get_all_metrics(self):
        """Test getting all metrics together."""
        collector = MetricsCollector()

        # Add some counters and histograms
        collector.increment_counter("write_total", {"status": "success"})
        collector.record_histogram("read_duration", 1.5, {"channel": "working"})

        all_metrics = collector.get_all_metrics()

        assert "counters" in all_metrics
        assert "histograms" in all_metrics
        assert len(all_metrics["counters"]) == 1
        assert len(all_metrics["histograms"]) == 1

    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        collector = MetricsCollector()

        # Add some metrics
        collector.increment_counter("test_counter")
        collector.record_histogram("test_histogram", 1.0)

        assert len(collector.get_counters()) == 1
        assert len(collector.get_histograms()) == 1

        # Reset
        collector.reset()

        assert len(collector.get_counters()) == 0
        assert len(collector.get_histograms()) == 0

    def test_thread_safety(self):
        """Test that metrics collection is thread-safe."""
        collector = MetricsCollector()
        
        def increment_worker():
            for _ in range(100):
                collector.increment_counter("thread_test_counter", {"worker": threading.current_thread().name})

        def histogram_worker():
            for i in range(100):
                collector.record_histogram("thread_test_histogram", i * 0.01, {"worker": threading.current_thread().name})

        # Create multiple threads
        threads = []
        for i in range(5):
            t1 = threading.Thread(target=increment_worker, name=f"counter-{i}")
            t2 = threading.Thread(target=histogram_worker, name=f"histogram-{i}")
            threads.extend([t1, t2])

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        counters = collector.get_counters()
        histograms = collector.get_histograms()

        # Should have 5 counter entries (one per worker thread)
        counter_entries = [k for k in counters.keys() if "thread_test_counter" in k]
        assert len(counter_entries) == 5

        # Each counter should have count of 100
        for key in counter_entries:
            assert counters[key] == 100

        # Should have 5 histogram entries
        histogram_entries = [k for k in histograms.keys() if "thread_test_histogram" in k]
        assert len(histogram_entries) == 5

        # Each histogram should have count of 100
        for key in histogram_entries:
            assert histograms[key]["count"] == 100

    def test_histogram_statistics(self):
        """Test histogram statistical calculations."""
        collector = MetricsCollector()

        # Add various values
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            collector.record_histogram("stats_test", value)

        histograms = collector.get_histograms()
        data = histograms["stats_test"]

        assert data["count"] == 5
        assert data["sum"] == 15.0
        assert data["min"] == 1.0
        assert data["max"] == 5.0
        assert data["avg"] == 3.0

    def test_large_numbers(self):
        """Test metrics with large numbers."""
        collector = MetricsCollector()

        # Test large counter values
        for _ in range(1000000):
            collector.increment_counter("large_counter")

        counters = collector.get_counters()
        assert counters["large_counter"] == 1000000

        # Test large histogram values
        collector.record_histogram("large_histogram", 1000000.5)
        collector.record_histogram("large_histogram", 2000000.7)

        histograms = collector.get_histograms()
        data = histograms["large_histogram"]

        assert data["count"] == 2
        assert data["sum"] == 3000001.2
        assert data["min"] == 1000000.5
        assert data["max"] == 2000000.7

    def test_negative_histogram_values(self):
        """Test histogram with negative values."""
        collector = MetricsCollector()

        collector.record_histogram("negative_test", -1.5)
        collector.record_histogram("negative_test", 2.5)
        collector.record_histogram("negative_test", -0.5)

        histograms = collector.get_histograms()
        data = histograms["negative_test"]

        assert data["count"] == 3
        assert data["sum"] == 0.5  # -1.5 + 2.5 + (-0.5)
        assert data["min"] == -1.5
        assert data["max"] == 2.5
        assert abs(data["avg"] - 0.16666666666666666) < 1e-10  # 0.5 / 3

    def test_zero_values(self):
        """Test metrics with zero values."""
        collector = MetricsCollector()

        collector.record_histogram("zero_test", 0.0)
        collector.record_histogram("zero_test", 0.0)
        collector.record_histogram("zero_test", 1.0)

        histograms = collector.get_histograms()
        data = histograms["zero_test"]

        assert data["count"] == 3
        assert data["sum"] == 1.0
        assert data["min"] == 0.0
        assert data["max"] == 1.0

    def test_enable_disable(self):
        """Test enabling and disabling metrics collection."""
        collector = MetricsCollector()

        # Initially enabled
        assert collector.enabled is True

        collector.increment_counter("test1")
        assert len(collector.get_counters()) == 1

        # Disable
        collector.disable()
        assert collector.enabled is False

        collector.increment_counter("test2")
        collector.record_histogram("test_hist", 1.0)

        # Should not record when disabled
        counters = collector.get_counters()
        histograms = collector.get_histograms()
        assert len(counters) == 1  # Only test1
        assert len(histograms) == 0

        # Re-enable
        collector.enable()
        assert collector.enabled is True

        collector.increment_counter("test3")
        counters = collector.get_counters()
        assert len(counters) == 2  # test1 and test3


class TestGlobalMetrics:
    """Test global metrics functions."""

    @pytest.fixture(autouse=True)
    def reset_global_metrics(self):
        """Reset global metrics before each test."""
        metrics.reset_metrics()
        yield
        metrics.reset_metrics()

    def test_global_increment_counter(self):
        """Test global counter increment function."""
        metrics.increment_counter("global_test", {"status": "success"})
        metrics.increment_counter("global_test", {"status": "success"})

        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]

        assert "global_test{status='success'}" in counters
        assert counters["global_test{status='success'}"] == 2

    def test_global_record_histogram(self):
        """Test global histogram recording function."""
        metrics.record_histogram("global_duration", 1.5, {"operation": "read"})
        metrics.record_histogram("global_duration", 2.5, {"operation": "read"})

        all_metrics = metrics.get_all_metrics()
        histograms = all_metrics["histograms"]

        key = "global_duration{operation='read'}"
        assert key in histograms
        assert histograms[key]["count"] == 2
        assert histograms[key]["sum"] == 4.0

    def test_global_get_all_metrics(self):
        """Test getting all global metrics."""
        metrics.increment_counter("counter1")
        metrics.record_histogram("histogram1", 1.0)

        all_metrics = metrics.get_all_metrics()

        assert "counters" in all_metrics
        assert "histograms" in all_metrics
        assert "counter1" in all_metrics["counters"]
        assert "histogram1" in all_metrics["histograms"]

    def test_global_reset_metrics(self):
        """Test global metrics reset."""
        metrics.increment_counter("test_counter")
        metrics.record_histogram("test_histogram", 1.0)

        # Verify metrics exist
        all_metrics = metrics.get_all_metrics()
        assert len(all_metrics["counters"]) == 1
        assert len(all_metrics["histograms"]) == 1

        # Reset
        metrics.reset_metrics()

        # Verify metrics are cleared
        all_metrics = metrics.get_all_metrics()
        assert len(all_metrics["counters"]) == 0
        assert len(all_metrics["histograms"]) == 0

    def test_global_metrics_disabled(self):
        """Test global metrics when disabled."""
        # Disable metrics
        metrics._global_metrics.disable()

        metrics.increment_counter("disabled_counter")
        metrics.record_histogram("disabled_histogram", 1.0)

        all_metrics = metrics.get_all_metrics()
        assert len(all_metrics["counters"]) == 0
        assert len(all_metrics["histograms"]) == 0

        # Re-enable for cleanup
        metrics._global_metrics.enable()

    def test_global_enable_disable(self):
        """Test global metrics enable/disable functions."""
        assert metrics.is_enabled() is True

        metrics.disable_metrics()
        assert metrics.is_enabled() is False

        metrics.increment_counter("disabled_test")
        all_metrics = metrics.get_all_metrics()
        assert len(all_metrics["counters"]) == 0

        metrics.enable_metrics()
        assert metrics.is_enabled() is True

        metrics.increment_counter("enabled_test")
        all_metrics = metrics.get_all_metrics()
        assert len(all_metrics["counters"]) == 1


class TestMetricsIntegration:
    """Integration tests for metrics functionality."""

    @pytest.fixture(autouse=True)
    def reset_metrics(self):
        """Reset metrics before each test."""
        metrics.reset_metrics()
        yield
        metrics.reset_metrics()

    def test_realistic_aimemory_metrics(self):
        """Test metrics collection for realistic AIMemory operations."""
        # Simulate write operations
        for i in range(10):
            status = "success" if i < 8 else "error"
            channel = "working" if i % 2 == 0 else "routing"
            metrics.increment_counter("ai_memory_write_total", {
                "channel": channel,
                "status": status
            })

        # Simulate read operations with timing
        for i in range(15):
            channel = "working" if i % 3 == 0 else "routing"
            duration = 0.1 + (i * 0.05)  # Varying durations
            metrics.record_histogram("ai_memory_read_duration", duration, {
                "channel": channel
            })

        # Simulate checkpoint operations
        for _ in range(5):
            status = "success"
            metrics.increment_counter("ai_memory_checkpoint_total", {
                "operation": "set",
                "status": status
            })

        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        histograms = all_metrics["histograms"]

        # Verify write counters
        working_success = counters.get("ai_memory_write_total{channel='working',status='success'}", 0)
        working_error = counters.get("ai_memory_write_total{channel='working',status='error'}", 0)
        routing_success = counters.get("ai_memory_write_total{channel='routing',status='success'}", 0)
        routing_error = counters.get("ai_memory_write_total{channel='routing',status='error'}", 0)

        assert working_success == 4  # 5 working writes, 4 successful
        assert working_error == 1    # 1 working write error
        assert routing_success == 4  # 5 routing writes, 4 successful
        assert routing_error == 1    # 1 routing write error

        # Verify read histograms
        working_reads = histograms.get("ai_memory_read_duration{channel='working'}")
        routing_reads = histograms.get("ai_memory_read_duration{channel='routing'}")

        assert working_reads is not None
        assert routing_reads is not None
        assert working_reads["count"] == 5  # Every 3rd read (0, 3, 6, 9, 12)
        assert routing_reads["count"] == 10  # Remaining reads

        # Verify checkpoint counters
        checkpoint_success = counters.get("ai_memory_checkpoint_total{operation='set',status='success'}")
        assert checkpoint_success == 5

    def test_performance_under_load(self):
        """Test metrics performance under high load."""
        start_time = time.time()

        # Simulate high-frequency operations
        for i in range(10000):
            metrics.increment_counter("load_test_counter", {"iteration": str(i % 100)})
            if i % 10 == 0:
                metrics.record_histogram("load_test_histogram", i * 0.001, {"batch": str(i // 1000)})

        end_time = time.time()
        duration = end_time - start_time

        # Should complete reasonably quickly (under 5 seconds)
        assert duration < 5.0

        all_metrics = metrics.get_all_metrics()
        
        # Verify all metrics were recorded
        assert len(all_metrics["counters"]) == 100  # 100 different iteration labels
        assert len(all_metrics["histograms"]) == 10  # 10 different batch labels

        # Verify counter totals
        total_counter_value = sum(all_metrics["counters"].values())
        assert total_counter_value == 10000

    def test_memory_usage_stability(self):
        """Test that metrics collection doesn't cause memory leaks."""
        # Record initial metrics state
        initial_metrics = metrics.get_all_metrics()
        initial_counter_count = len(initial_metrics["counters"])
        initial_histogram_count = len(initial_metrics["histograms"])

        # Perform many operations with same labels (should not grow unbounded)
        for _ in range(1000):
            metrics.increment_counter("stable_counter", {"type": "test"})
            metrics.record_histogram("stable_histogram", 1.0, {"type": "test"})

        # Check that we only added expected metrics
        final_metrics = metrics.get_all_metrics()
        final_counter_count = len(final_metrics["counters"])
        final_histogram_count = len(final_metrics["histograms"])

        assert final_counter_count == initial_counter_count + 1
        assert final_histogram_count == initial_histogram_count + 1

        # Verify the values are correct
        counter_value = final_metrics["counters"]["stable_counter{type='test'}"]
        histogram_data = final_metrics["histograms"]["stable_histogram{type='test'}"]

        assert counter_value == 1000
        assert histogram_data["count"] == 1000

    def test_concurrent_access_safety(self):
        """Test that concurrent access to metrics is safe."""
        def worker(worker_id):
            for i in range(100):
                metrics.increment_counter("concurrent_counter", {"worker": str(worker_id)})
                metrics.record_histogram("concurrent_histogram", i * 0.01, {"worker": str(worker_id)})

        # Start multiple worker threads
        threads = []
        num_workers = 10
        
        for worker_id in range(num_workers):
            thread = threading.Thread(target=worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # Wait for all workers to complete
        for thread in threads:
            thread.join()

        # Verify results
        all_metrics = metrics.get_all_metrics()
        counters = all_metrics["counters"]
        histograms = all_metrics["histograms"]

        # Should have one counter and histogram per worker
        assert len(counters) == num_workers
        assert len(histograms) == num_workers

        # Each counter should have value 100
        for worker_id in range(num_workers):
            counter_key = f"concurrent_counter{{worker='{worker_id}'}}"
            histogram_key = f"concurrent_histogram{{worker='{worker_id}'}}"
            
            assert counters[counter_key] == 100
            assert histograms[histogram_key]["count"] == 100

    def test_edge_case_labels(self):
        """Test metrics with edge case label values."""
        # Test with special characters in labels
        metrics.increment_counter("special_chars", {
            "path": "/api/v1/test",
            "method": "POST",
            "status": "200"
        })

        # Test with empty string labels
        metrics.increment_counter("empty_labels", {"empty": ""})

        # Test with numeric labels (converted to strings)
        metrics.record_histogram("numeric_labels", 1.5, {"port": "8080", "timeout": "30"})

        all_metrics = metrics.get_all_metrics()
        
        # Verify all metrics were recorded properly
        assert len(all_metrics["counters"]) == 2
        assert len(all_metrics["histograms"]) == 1

        # Check specific label formatting
        special_key = "special_chars{method='POST',path='/api/v1/test',status='200'}"
        assert special_key in all_metrics["counters"]
