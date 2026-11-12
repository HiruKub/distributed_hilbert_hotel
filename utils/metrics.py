import statistics
import time
import tracemalloc

MIB = 1024 * 1024


def timed(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - start


def per_call_time(fn, args_list):
    if not args_list:
        return 0.0
    start = time.perf_counter()
    for args in args_list:
        fn(*args)
    return (time.perf_counter() - start) / len(args_list)


def measure_memory(fn, *args, **kwargs):
    started_here = not tracemalloc.is_tracing()
    if started_here:
        tracemalloc.start()
    base_current, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    try:
        result = fn(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        if started_here:
            tracemalloc.stop()
    return result, (current - base_current) / MIB, (peak - base_current) / MIB


def summarize(values):
    """สรุปค่าหลายรอบ: mean, min, max, median"""
    values = list(values)
    if not values:
        return {"mean": 0.0, "min": 0.0, "max": 0.0, "median": 0.0}
    return {
        "mean": statistics.fmean(values),
        "min": min(values),
        "max": max(values),
        "median": statistics.median(values),
    }
