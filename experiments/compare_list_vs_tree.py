import argparse
import csv
import os
import sys
import time
import statistics
import tracemalloc

# ให้ import ทั้ง core และ experiments ได้จาก root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import core.hotel_system as list_system
import experiments.tree_version.hotel_system_tree as tree_system
from utils.reports import list_rooms, load_stats


MIB = 1024 * 1024
SEARCH_BATCH = 1000


def timed(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - start


def measure_memory(fn, *args, **kwargs):
    started = not tracemalloc.is_tracing()
    if started:
        tracemalloc.start()
    base_current, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    try:
        result = fn(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
    finally:
        if started:
            tracemalloc.stop()
    return result, (current - base_current) / MIB, (peak - base_current) / MIB


def per_call_time(fn, args_list):
    if not args_list:
        return 0.0
    start = time.perf_counter()
    for args in args_list:
        fn(*args)
    return (time.perf_counter() - start) / len(args_list)


def build_hotel(hs_module, N, V, K, mode, salt):
    s_list = [K // 10] * 10
    hotel, t_ring = timed(hs_module.HotelSystem, N, V, 10, s_list, mode=mode, salt=str(salt))
    return hotel, t_ring


def benchmark_single_version(hs_module, N=10, V=32, K=10_000, salt="0"):
    mode = hs_module.HashType.HASH_RING

    # 1. จัดแขกและสร้างวงแหวน (Median of 3)
    ring_times = []
    for _ in range(3):
        _, t_r = build_hotel(hs_module, N, V, K, mode, salt)
        ring_times.append(t_r)
    t_place = statistics.median(ring_times)

    # 2. ค้นหา 1,000 ครั้ง
    hotel, _ = build_hotel(hs_module, N, V, K, mode, salt)
    keys = list(hotel.guests_by_id)
    picks = [keys[(i * 7919) % len(keys)] for i in range(min(SEARCH_BATCH, len(keys)))]
    room_args = [(hotel.guests_by_id[k].node_id, hotel.guests_by_id[k].room_no) for k in picks]

    t_id_search = per_call_time(hotel.search_by_id, picks) * 1e6      # µs
    t_room_search = per_call_time(hotel.search_by_node_room, room_args) * 1e6  # µs
    t_route = per_call_time(hotel.router.get_node, picks) * 1e6       # µs

    # 3. จัดเรียงห้องพัก
    _, t_sort = timed(list_rooms, hotel)

    # 4. ความสมดุลของโหลด (CV)
    stats = load_stats(hotel)
    cv_val = stats.cv if stats.cv is not None else 0.0

    # 5. เพิ่มอาคาร (Add Node) และ ลบอาคาร (Remove Node)
    add_times = []
    for r in range(3):
        h_tmp, _ = build_hotel(hs_module, N, V, K, mode, salt)
        rep_add, elapsed_add = timed(h_tmp.add_node, f"NewNode_{r}")
        add_times.append((elapsed_add, rep_add.migrated_count, rep_add.migration_rate))
    t_add = statistics.median([x[0] for x in add_times])
    add_count = add_times[0][1]
    add_rate = add_times[0][2]

    rem_times = []
    for r in range(3):
        h_tmp, _ = build_hotel(hs_module, N, V, K, mode, salt)
        rep_rem, elapsed_rem = timed(h_tmp.remove_node, "1")
        rem_times.append((elapsed_rem, rep_rem.migrated_count, rep_rem.migration_rate))
    t_rem = statistics.median([x[0] for x in rem_times])
    rem_count = rem_times[0][1]
    rem_rate = rem_times[0][2]

    # 6. วัดหน่วยความจำ (tracemalloc)
    _, cur_mem, peak_mem = measure_memory(build_hotel, hs_module, N, V, K, mode, salt)

    return {
        "placement_time_s": t_place,
        "search_by_id_us": t_id_search,
        "search_by_room_us": t_room_search,
        "route_lookup_us": t_route,
        "sort_rooms_s": t_sort,
        "add_node_time_s": t_add,
        "remove_node_time_s": t_rem,
        "add_migrated_count": add_count,
        "add_migration_rate": add_rate,
        "remove_migrated_count": rem_count,
        "remove_migration_rate": rem_rate,
        "load_cv": cv_val,
        "memory_current_mib": cur_mem,
        "memory_peak_mib": peak_mem
    }


def calculate_diff_and_percent(val_list, val_tree, lower_is_better=True):
    """
    คำนวณผลต่าง และเปอร์เซ็นต์ผลกระทบ (% change relative to List)
    Percent = ((Tree - List) / List) * 100%
    """
    if val_list == 0:
        pct = 0.0
    else:
        pct = ((val_tree - val_list) / abs(val_list)) * 100.0

    ratio = (val_tree / val_list) if val_list > 0 else 0.0

    if lower_is_better:
        if pct > 0:
            conclusion = f"Tree ช้า/เปลืองกว่า (+{pct:.2f}% | {ratio:.2f}x)"
        elif pct < 0:
            conclusion = f"Tree เร็ว/ประหยัดกว่า ({pct:.2f}% | {ratio:.2f}x)"
        else:
            conclusion = "เท่ากัน (0.00%)"
    else:
        conclusion = f"{'+' if pct >= 0 else ''}{pct:.2f}%"

    return pct, ratio, conclusion


def run_comparison_benchmark(K_values=[1_000, 10_000], N=10, V=32, salt="0", out_csv=None):
    print("=" * 105)
    print("    การเปรียบเทียบเชิงประสิทธิภาพหน่วยต่อหน่วย: Core (List+Bisect) vs Tree (AVL Tree)")
    print(f"      พารามิเตอร์ทดสอบ: อาคารเริ่มต้น N={N}, จุดเสมือน V={V}, Salt={salt}")
    print("=" * 105)

    all_comparison_rows = []

    metrics_def = [
        ("เวลาจัดแขกเริ่มต้น (Placement)", "placement_time_s", "s", True),
        ("เวลาค้นหาด้วยรหัสแขก (Search ID)", "search_by_id_us", "µs", True),
        ("เวลาค้นหาด้วยห้องพัก (Search Room)", "search_by_room_us", "µs", True),
        ("เวลาหาอาคารบนวงแหวน (Routing)", "route_lookup_us", "µs", True),
        ("เวลาเรียงลำดับรายการห้อง (Sort)", "sort_rooms_s", "s", True),
        ("เวลาเพิ่มอาคาร 1 หลัง (Add Node)", "add_node_time_s", "s", True),
        ("เวลาลบอาคาร 1 หลัง (Remove Node)", "remove_node_time_s", "s", True),
        ("หน่วยความจำ Peak (tracemalloc)", "memory_peak_mib", "MiB", True),
        ("ความสมดุลของโหลด (Load CV)", "load_cv", "ratio", True),
        ("อัตราการย้ายเมื่อเพิ่มอาคาร (Rate)", "add_migration_rate", "rate", False),
        ("อัตราการย้ายเมื่อลบอาคาร (Rate)", "remove_migration_rate", "rate", False),
    ]

    for K in K_values:
        print(f"\n [กำลังทดสอบขนาดแขก K = {K:,} คน...]")
        res_list = benchmark_single_version(list_system, N=N, V=V, K=K, salt=salt)
        res_tree = benchmark_single_version(tree_system, N=N, V=V, K=K, salt=salt)

        print("-" * 105)
        print(f"{'ตัววัด / รายการทดสอบ':<35} | {'List (Core)':<14} | {'Tree (AVL)':<14} | {'หน่วย':<6} | {'ผลต่าง (%) และ สรุป':<30}")
        print("-" * 105)

        for label, key, unit, lower_is_better in metrics_def:
            val_l = res_list[key]
            val_t = res_tree[key]
            pct, ratio, concl = calculate_diff_and_percent(val_l, val_t, lower_is_better)

            fmt = ".4f" if unit in ["s", "MiB", "rate", "ratio"] else ".2f"
            str_l = f"{val_l:{fmt}}"
            str_t = f"{val_t:{fmt}}"

            print(f"{label:<35} | {str_l:<14} | {str_t:<14} | {unit:<6} | {concl:<30}")

            all_comparison_rows.append({
                "K": K,
                "metric_label": label,
                "metric_key": key,
                "unit": unit,
                "list_core_value": val_l,
                "tree_value": val_t,
                "difference_percent": round(pct, 2),
                "ratio_tree_to_list": round(ratio, 2),
                "summary": concl
            })

    print("=" * 105)

    if out_csv:
        os.makedirs(os.path.dirname(os.path.abspath(out_csv)), exist_ok=True)
        fieldnames = [
            "K", "metric_label", "metric_key", "unit",
            "list_core_value", "tree_value", "difference_percent",
            "ratio_tree_to_list", "summary"
        ]
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_comparison_rows)
        print(f" บันทึกตารางเปรียบเทียบฉบับสมบูรณ์เรียบร้อยที่: {out_csv}")


def main():
    parser = argparse.ArgumentParser(description="เปรียบเทียบ Core (List+Bisect) กับ Tree (AVL Tree) หน่วยต่อหน่วย")
    parser.add_argument("--quick", action="store_true", help="ทดสอบขนาดเล็ก (K=1,000, 5,000)")
    parser.add_argument("-k", "--guests", type=int, nargs="+", default=None)
    parser.add_argument("--out", default=os.path.join(PROJECT_ROOT, "experiments", "results", "comparison_list_vs_tree.csv"))
    args = parser.parse_args()

    if args.guests:
        k_values = args.guests
    elif args.quick:
        k_values = [1_000, 5_000]
    else:
        k_values = [1_000, 10_000]

    run_comparison_benchmark(K_values=k_values, out_csv=args.out)


if __name__ == "__main__":
    main()
