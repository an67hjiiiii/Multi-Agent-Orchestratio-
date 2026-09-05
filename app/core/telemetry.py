from __future__ import annotations

import math
import os
import subprocess


_BYTES_PER_MB = 1024 * 1024
_NVIDIA_SMI_COMMAND = [
    "nvidia-smi",
    "--query-gpu=memory.used",
    "--format=csv,noheader,nounits",
]


def _non_negative_mb(value: object) -> float | None:
    """Return a finite, non-negative memory value rounded to two decimals."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return round(number, 2)


def process_rss_mb() -> float | None:
    """Read the current process RSS in MiB when psutil is available."""
    try:
        import psutil  # type: ignore

        rss_bytes = psutil.Process(os.getpid()).memory_info().rss
        return _non_negative_mb(rss_bytes / _BYTES_PER_MB)
    except Exception:
        # Telemetry must not make a run fail on a minimal or unsupported host.
        return None


def gpu_memory_mb() -> float | None:
    """Return the largest visible NVIDIA device ``memory.used`` value in MiB.

    ``None`` is the explicit N/A value for CPU-only machines, missing
    ``nvidia-smi``, command failures, and unusable command output.
    """
    try:
        proc = subprocess.run(
            _NVIDIA_SMI_COMMAND,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode != 0:
            return None

        values: list[float] = []
        for line in (proc.stdout or "").splitlines():
            value = _non_negative_mb(line.strip())
            if value is not None:
                values.append(value)
        return max(values) if values else None
    except Exception:
        # GPU telemetry is best effort and must never block the pipeline.
        return None
