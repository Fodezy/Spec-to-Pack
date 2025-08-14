"""
Performance Tests for Balanced Pack Generation

These tests establish performance baselines and monitor for regressions
as required by M2.E3 — PERF-1.
"""

import json
import os
import statistics
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from studio.app import StudioApp
from studio.types import PackType


class PerformanceMetrics:
    """Performance metrics collector and analyzer."""

    def __init__(self):
        self.measurements: list[dict[str, Any]] = []

    def record_measurement(self, test_name: str, duration_ms: int,
                          artifacts_count: int, **kwargs):
        """Record a performance measurement."""
        self.measurements.append({
            'test_name': test_name,
            'timestamp': datetime.utcnow().isoformat(),
            'duration_ms': duration_ms,
            'artifacts_count': artifacts_count,
            **kwargs
        })

    def get_p95(self, test_name: str) -> float:
        """Get p95 duration for a specific test."""
        durations = [m['duration_ms'] for m in self.measurements
                    if m['test_name'] == test_name]
        if not durations:
            return 0.0
        durations.sort()
        p95_index = int(0.95 * len(durations))
        return durations[p95_index] / 1000.0  # Convert to seconds

    def get_statistics(self, test_name: str) -> dict[str, float]:
        """Get statistical summary for a test."""
        durations = [m['duration_ms'] for m in self.measurements
                    if m['test_name'] == test_name]
        if not durations:
            return {}

        return {
            'count': len(durations),
            'min_ms': min(durations),
            'max_ms': max(durations),
            'mean_ms': statistics.mean(durations),
            'median_ms': statistics.median(durations),
            'p95_ms': durations[int(0.95 * len(durations))] if len(durations) >= 20 else max(durations),
            'p99_ms': durations[int(0.99 * len(durations))] if len(durations) >= 100 else max(durations)
        }

    def save_baseline(self, filepath: Path):
        """Save performance baseline to file."""
        with open(filepath, 'w') as f:
            json.dump(self.measurements, f, indent=2)

    def load_baseline(self, filepath: Path):
        """Load performance baseline from file."""
        if filepath.exists():
            with open(filepath) as f:
                self.measurements = json.load(f)


class TestBalancedPackPerformance:
    """Performance test suite for balanced pack generation."""

    @classmethod
    def setup_class(cls):
        """Set up performance testing environment."""
        cls.app = StudioApp()
        cls.metrics = PerformanceMetrics()
        cls.fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"

        # Performance test configuration
        cls.BASELINE_P95_SECONDS = 8.0  # As per R3 requirement
        cls.REGRESSION_THRESHOLD = 0.20  # 20% regression budget
        cls.SAMPLE_SIZE = 10  # Samples for statistical significance

    def test_balanced_pack_p95_baseline(self):
        """
        Establish and validate p95 baseline for balanced pack generation.

        Requirements:
        - p95 ≤ 8s (warm) per R3
        - Failure if >20% regression vs baseline
        """
        measurements = []

        for run_idx in range(self.SAMPLE_SIZE):
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)

                # Warm-up run (cache templates, etc.)
                if run_idx == 0:
                    self._perform_generation(output_dir, warm_up=True)

                # Measured run
                start_time = time.time()
                artifact_index = self._perform_generation(output_dir)
                end_time = time.time()

                duration_ms = int((end_time - start_time) * 1000)
                measurements.append(duration_ms)

                # Record measurement
                self.metrics.record_measurement(
                    test_name='balanced_pack_p95_baseline',
                    duration_ms=duration_ms,
                    artifacts_count=len(artifact_index.artifacts),
                    run_index=run_idx
                )

        # Calculate p95
        measurements.sort()
        p95_ms = measurements[int(0.95 * len(measurements))]
        p95_seconds = p95_ms / 1000.0

        # Report performance metrics
        stats = {
            'min_ms': min(measurements),
            'max_ms': max(measurements),
            'mean_ms': statistics.mean(measurements),
            'p95_ms': p95_ms,
            'p95_seconds': p95_seconds
        }

        print("\nBalanced Pack Performance Baseline:")
        print(f"  Samples: {len(measurements)}")
        print(f"  Min: {stats['min_ms']}ms")
        print(f"  Mean: {stats['mean_ms']:.0f}ms")
        print(f"  Max: {stats['max_ms']}ms")
        print(f"  P95: {stats['p95_ms']}ms ({p95_seconds:.2f}s)")

        # Check baseline requirement
        assert p95_seconds <= self.BASELINE_P95_SECONDS, \
            f"P95 baseline exceeded: {p95_seconds:.2f}s > {self.BASELINE_P95_SECONDS}s"

        # Save baseline for regression testing
        baseline_path = Path(__file__).parent / "baseline_measurements.json"
        self.metrics.save_baseline(baseline_path)

        # Check for regression vs previous baseline
        self._check_performance_regression(p95_seconds, baseline_path)

    def test_artifact_completeness_performance(self):
        """
        Verify artifact generation performance meets completeness requirements.

        Tests that all required artifacts are generated within performance budget.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            start_time = time.time()
            artifact_index = self._perform_generation(output_dir)
            generation_time = time.time() - start_time

            # Verify artifact completeness
            expected_artifact_names = {
                'brief', 'prd', 'test_plan', 'roadmap',
                'lifecycle_diagram', 'sequence_diagram'
            }

            actual_artifact_names = {artifact.name for artifact in artifact_index.artifacts}

            # Check completeness
            missing_artifacts = expected_artifact_names - actual_artifact_names
            assert not missing_artifacts, f"Missing artifacts: {missing_artifacts}"

            # Record performance for completeness
            self.metrics.record_measurement(
                test_name='artifact_completeness_performance',
                duration_ms=int(generation_time * 1000),
                artifacts_count=len(artifact_index.artifacts),
                expected_count=len(expected_artifact_names),
                actual_count=len(actual_artifact_names)
            )

            print(f"Artifact completeness: {len(artifact_index.artifacts)} artifacts in {generation_time:.2f}s")

    def test_offline_mode_performance(self):
        """
        Verify offline mode performance characteristics.

        Offline mode should be deterministic and fast (no network delays).
        """
        measurements = []

        for _ in range(5):  # Smaller sample for offline testing
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)

                start_time = time.time()
                artifact_index = self.app.generate_from_files(
                    idea_path=self.fixtures_dir / "idea_card.yaml",
                    decisions_path=self.fixtures_dir / "decision_sheet.yaml",
                    pack=PackType.BALANCED,
                    out_dir=output_dir,
                    offline=True  # Explicitly test offline performance
                )
                end_time = time.time()

                duration_ms = int((end_time - start_time) * 1000)
                measurements.append(duration_ms)

                assert artifact_index is not None
                assert len(artifact_index.artifacts) > 0

        # Offline should be consistent and fast
        max_duration = max(measurements)
        min_duration = min(measurements)
        variance = max_duration - min_duration

        print(f"Offline mode performance: {min_duration}-{max_duration}ms (variance: {variance}ms)")

        # Offline mode should be reasonably consistent
        assert variance < 2000, f"High variance in offline mode: {variance}ms"

    def test_memory_efficiency(self):
        """
        Basic memory efficiency test for balanced pack generation.
        """
        import os

        import psutil

        process = psutil.Process(os.getpid())

        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Generate pack and measure memory
            artifact_index = self._perform_generation(output_dir)
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB

            memory_usage = peak_memory - baseline_memory

            self.metrics.record_measurement(
                test_name='memory_efficiency',
                duration_ms=0,  # Not timing-focused
                artifacts_count=len(artifact_index.artifacts),
                baseline_memory_mb=baseline_memory,
                peak_memory_mb=peak_memory,
                memory_usage_mb=memory_usage
            )

            print(f"Memory usage: {memory_usage:.1f}MB for {len(artifact_index.artifacts)} artifacts")

            # Reasonable memory usage (adjust based on requirements)
            assert memory_usage < 100, f"Excessive memory usage: {memory_usage:.1f}MB"

    def _perform_generation(self, output_dir: Path, warm_up: bool = False) -> Any:
        """Perform a standard balanced pack generation."""
        return self.app.generate_from_files(
            idea_path=self.fixtures_dir / "idea_card.yaml",
            decisions_path=self.fixtures_dir / "decision_sheet.yaml",
            pack=PackType.BALANCED,
            out_dir=output_dir,
            offline=True  # Ensure consistent, network-free performance
        )

    def _check_performance_regression(self, current_p95: float, baseline_path: Path):
        """Check for performance regression vs stored baseline."""
        if not baseline_path.exists():
            print("No baseline found - creating new baseline")
            return

        # Load previous baseline
        previous_metrics = PerformanceMetrics()
        previous_metrics.load_baseline(baseline_path)

        # Get previous p95
        previous_p95 = previous_metrics.get_p95('balanced_pack_p95_baseline')

        if previous_p95 > 0:
            regression_ratio = (current_p95 - previous_p95) / previous_p95

            print("Performance comparison:")
            print(f"  Previous P95: {previous_p95:.2f}s")
            print(f"  Current P95: {current_p95:.2f}s")
            print(f"  Regression: {regression_ratio:.1%}")

            # Check regression threshold
            if regression_ratio > self.REGRESSION_THRESHOLD:
                pytest.fail(
                    f"Performance regression exceeds threshold: "
                    f"{regression_ratio:.1%} > {self.REGRESSION_THRESHOLD:.1%}"
                )


# CI Integration Performance Tests
class TestCIPerformanceIntegration:
    """Performance tests specifically for CI environment integration."""

    def test_ci_performance_budget(self):
        """
        Verify performance meets CI budget requirements.

        This test is designed to run in CI and fail builds that
        exceed performance budgets.
        """
        app = StudioApp()
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"

        # CI typically has different performance characteristics
        ci_mode = os.environ.get('CI', '').lower() in ('true', '1', 'yes')
        if ci_mode:
            budget_multiplier = 2.0  # Allow 2x time in CI environment
            print("Running in CI mode - applying performance budget multiplier")
        else:
            budget_multiplier = 1.0

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            start_time = time.time()
            artifact_index = app.generate_from_files(
                idea_path=fixtures_dir / "idea_card.yaml",
                decisions_path=fixtures_dir / "decision_sheet.yaml",
                pack=PackType.BALANCED,
                out_dir=output_dir,
                offline=True
            )
            generation_time = time.time() - start_time

            # CI performance budget
            ci_budget_seconds = 8.0 * budget_multiplier

            assert generation_time <= ci_budget_seconds, \
                f"CI performance budget exceeded: {generation_time:.2f}s > {ci_budget_seconds:.2f}s"

            assert artifact_index is not None
            assert len(artifact_index.artifacts) > 0

            print(f"CI performance: {generation_time:.2f}s (budget: {ci_budget_seconds:.2f}s)")

    def test_deterministic_performance_in_ci(self):
        """
        Verify performance is deterministic across CI runs.

        This helps catch performance variations that could
        affect CI reliability.
        """
        app = StudioApp()
        fixtures_dir = Path(__file__).parent.parent.parent / "fixtures"

        measurements = []

        # Multiple runs to check consistency
        for _ in range(3):  # Limited for CI time constraints
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)

                start_time = time.time()
                artifact_index = app.generate_from_files(
                    idea_path=fixtures_dir / "idea_card.yaml",
                    decisions_path=fixtures_dir / "decision_sheet.yaml",
                    pack=PackType.BALANCED,
                    out_dir=output_dir,
                    offline=True
                )
                end_time = time.time()

                measurements.append(end_time - start_time)
                assert artifact_index is not None

        # Check consistency
        min_time = min(measurements)
        max_time = max(measurements)
        variance = max_time - min_time

        print(f"CI consistency: {min_time:.2f}s - {max_time:.2f}s (variance: {variance:.2f}s)")

        # Performance should be reasonably consistent in CI
        # Allow for some variance due to CI environment factors
        max_variance = 5.0  # seconds
        assert variance <= max_variance, \
            f"High performance variance in CI: {variance:.2f}s > {max_variance}s"
