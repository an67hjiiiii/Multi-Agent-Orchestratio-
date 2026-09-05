from __future__ import annotations
import os
import subprocess


def process_rss_mb() -> float | None:
    try:
        import psutil  # type: ignore
        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return None


def gpu_memory_mb() -> float | None:
    """Best-effort NVIDIA process/device memory snapshot; N/A is valid on CPU-only machines."""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if proc.returncode != 0:
            return None
        vals = [float(x.strip()) for x in proc.stdout.splitlines() if x.strip()]
        return max(vals) if vals else None
    except Exception:
        return None
