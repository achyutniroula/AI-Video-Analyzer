"""
TimingProfiler — per-step timing for one frame pass through the pipeline.

Usage:
    profiler = TimingProfiler()

    with profiler.step("siglip"):
        output = siglip(frame, ...)

    with profiler.step("panoptic"):
        output = panoptic(frame, ...)

    print(profiler.summary(frame_id=0, target_s=5.0))
    assert profiler.passes_target(5.0)
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Dict, List, Optional


class TimingProfiler:
    """Records wall-clock time for each named step in a pipeline pass."""

    def __init__(self):
        self._steps: Dict[str, float] = {}   # name → elapsed seconds
        self._order: List[str] = []           # insertion order

    @contextmanager
    def step(self, name: str):
        """
        Context manager — times the block and stores the result.

        Example:
            with profiler.step("siglip"):
                output = siglip(frame, ...)
        """
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - t0
            self._steps[name] = elapsed
            if name not in self._order:
                self._order.append(name)

    def record(self, name: str, elapsed_s: float):
        """Manually record a pre-measured step (e.g. from PerceptionOutput.processing_time)."""
        self._steps[name] = elapsed_s
        if name not in self._order:
            self._order.append(name)

    # ─────────────────────────────────────────────────────────────────
    #  Accessors
    # ─────────────────────────────────────────────────────────────────

    def total(self) -> float:
        return sum(self._steps.values())

    def get(self, name: str) -> Optional[float]:
        return self._steps.get(name)

    def to_dict(self) -> Dict[str, float]:
        return {n: self._steps[n] for n in self._order}

    def passes_target(self, target_s: float = 5.0) -> bool:
        return self.total() <= target_s

    # ─────────────────────────────────────────────────────────────────
    #  Formatted report
    # ─────────────────────────────────────────────────────────────────

    def summary(
        self,
        frame_id: Optional[int] = None,
        timestamp: Optional[float] = None,
        target_s: float = 5.0,
    ) -> str:
        total = self.total()
        status = "PASS" if total <= target_s else "FAIL"

        hdr_parts = []
        if frame_id is not None:
            hdr_parts.append(f"Frame {frame_id}")
        if timestamp is not None:
            hdr_parts.append(f"t={timestamp:.2f}s")
        hdr_parts.append(f"{status}  {total:.2f}s / {target_s:.1f}s target")
        header = "  ".join(hdr_parts)

        col_w = max(len(n) for n in self._order) + 2 if self._order else 12
        col_w = max(col_w, 14)

        lines = [
            f"\n{'─' * (col_w + 26)}",
            f"  {header}",
            f"{'─' * (col_w + 26)}",
            f"  {'Step':<{col_w}}  {'Time (s)':>8}  {'% total':>8}",
            f"  {'─' * col_w}  {'─' * 8}  {'─' * 8}",
        ]

        for name in self._order:
            t = self._steps[name]
            pct = (t / total * 100) if total > 0 else 0.0
            lines.append(f"  {name:<{col_w}}  {t:>8.3f}  {pct:>7.1f}%")

        lines += [
            f"  {'─' * col_w}  {'─' * 8}  {'─' * 8}",
            f"  {'TOTAL':<{col_w}}  {total:>8.3f}  {'100.0%':>8}",
            f"{'─' * (col_w + 26)}",
        ]
        return "\n".join(lines)

    def reset(self):
        self._steps.clear()
        self._order.clear()
