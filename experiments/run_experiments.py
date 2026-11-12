import argparse
import datetime
import os
import platform
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.hotel_system import HashType, HotelSystem  # noqa: E402
from utils.exporter import export_guests, export_migrations, write_csv  # noqa: E402
from utils.metrics import measure_memory, per_call_time, timed  # noqa: E402
from utils.reports import list_rooms, load_stats, sorted_node_ids, verify_consistency  # noqa: E402

NUM_CHANNELS = 10
DEFAULT_SALTS = (0, 1, 2)
SEARCH_BATCH = 1000
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultsTree")

RING = HashType.HASH_RING
MOD_N = HashType.HASH_MOD_N
METHOD_NAME = {RING: "ring", MOD_N: "mod_n"}

FIELDS_A = ["experiment", "salt", "N", "V", "K", "method", "channels",
            "t_build_ring_s", "t_place_guests_s", "t_sort_s",
            "t_search_by_id_us", "t_search_by_room_us", "t_route_only_us",
            "search_batch", "mem_current_mib", "mem_peak_mib"]

FIELDS_B = ["experiment", "salt", "N", "V", "K", "method", "operation", "node_id",
            "migrated_count", "migration_rate", "expected_rate", "time_s",
            "only_expected_nodes_move", "total_guests_after", "index_consistent"]

FIELDS_C = ["experiment", "salt", "N", "V", "K", "method", "ring_points",
            "guests_per_node", "max", "min", "mean", "std", "cv",
            "t_build_ring_s", "t_place_guests_s",
            "mem_ring_current_mib", "mem_ring_peak_mib",
            "mem_total_current_mib", "mem_total_peak_mib",
            "add_migrated", "add_rate", "remove_migrated", "remove_rate"]


# ---------------------------------------------------------------- พื้นฐาน

def channel_counts(K, channels=NUM_CHANNELS):
    base, extra = divmod(K, channels)
    return [base + (1 if i < extra else 0) for i in range(channels)]


def build_hotel_timed(N, V, K, mode, salt):
    hotel, t_ring = timed(HotelSystem, N, V, 0, [], mode=mode, salt=str(salt))

    def place():
        for c, count in enumerate(channel_counts(K), start=1):
            hotel.add_guest_group(c, 1, count)

    _, t_place = timed(place)
    return hotel, t_ring, t_place


def _r(x, digits=9):
    return None if x is None else round(x, digits)


# ---------------------------------------------------------------- Benchmark (ใช้ร่วมกับเมนู CLI)

def benchmark_once(N, V, K, mode, salt, with_memory=True):
    hotel, t_ring, t_place = build_hotel_timed(N, V, K, mode, salt)

    keys = list(hotel.guests_by_id)
    n = len(keys)
    if n:
        picks = [keys[(i * 7919) % n] for i in range(SEARCH_BATCH)]
        room_args = [(hotel.guests_by_id[k].node_id, hotel.guests_by_id[k].room_no) for k in picks]
        t_id = per_call_time(hotel.search_by_id, picks)
        t_room = per_call_time(hotel.search_by_node_room, room_args)
        t_route = per_call_time(hotel.router.get_node, picks)
    else:
        t_id = t_room = t_route = 0.0

    _, t_sort = timed(list_rooms, hotel)
    del hotel

    row = {
        "experiment": "A", "salt": str(salt), "N": N, "V": V, "K": K,
        "method": METHOD_NAME[mode], "channels": NUM_CHANNELS,
        "t_build_ring_s": _r(t_ring), "t_place_guests_s": _r(t_place),
        "t_sort_s": _r(t_sort),
        "t_search_by_id_us": _r(t_id * 1e6, 4),
        "t_search_by_room_us": _r(t_room * 1e6, 4),
        "t_route_only_us": _r(t_route * 1e6, 4),
        "search_batch": SEARCH_BATCH,
        "mem_current_mib": None, "mem_peak_mib": None,
    }
    if with_memory:
        _, cur, peak = measure_memory(build_hotel_timed, N, V, K, mode, salt)
        row["mem_current_mib"] = _r(cur, 4)
        row["mem_peak_mib"] = _r(peak, 4)
    return row


# ---------------------------------------------------------------- การย้ายอาคาร (ใช้ร่วมกับเมนู CLI)

def run_b_case(N, V, K, mode, salt):
    method = METHOD_NAME[mode]
    add_id = str(N + 1)
    remove_id = str((N + 1) // 2)
    rows = []

    for operation, node_id in (("add", add_id), ("remove", remove_id)):
        hotel, _, _ = build_hotel_timed(N, V, K, mode, salt)
        action = hotel.add_node if operation == "add" else hotel.remove_node
        report, elapsed = timed(action, node_id)

        if operation == "add":
            only_expected = all(m.new_node == node_id for m in report.migrations)
            expected = 1 / (N + 1)
        else:
            only_expected = all(m.old_node == node_id for m in report.migrations)
            expected = 1 / N

        total_after = len(hotel.guests_by_id)
        index_sum = sum(len(s) for s in hotel.guests_by_node.values())
        consistent = (not verify_consistency(hotel)
                      and total_after == K and index_sum == K
                      and report.migrated_count == len(report.migrations))

        rows.append({
            "experiment": "B", "salt": str(salt), "N": N, "V": V, "K": K,
            "method": method, "operation": operation, "node_id": node_id,
            "migrated_count": report.migrated_count,
            "migration_rate": _r(report.migration_rate, 6) if K > 0 else None,
            "expected_rate": _r(expected, 6),
            "time_s": _r(elapsed),
            "only_expected_nodes_move": only_expected,
            "total_guests_after": total_after,
            "index_consistent": consistent,
        })
    return rows


# ---------------------------------------------------------------- การทดลอง A / B / C

def run_experiment_a(Ks, salts, N=10, V=32, log=print):
    rows = []
    for K in Ks:
        for salt in salts:
            log(f"[A] K={K:>7,}  salt={salt}")
            rows.append(benchmark_once(N, V, K, RING, salt))
    return rows


def run_experiment_b(Ns, salts, K=10_000, V=32, log=print):
    rows = []
    for N in Ns:
        for salt in salts:
            for mode in (RING, MOD_N):
                log(f"[B] N={N:>2}  salt={salt}  {METHOD_NAME[mode]}")
                rows.extend(run_b_case(N, V, K, mode, salt))
    return rows


def run_experiment_c(Vs, salts, N=10, K=10_000, log=print):
    rows = []
    for V in Vs:
        for salt in salts:
            log(f"[C] V={V:>2}  salt={salt}")
            hotel, t_ring, t_place = build_hotel_timed(N, V, K, RING, salt)
            stats = load_stats(hotel)
            per_node = ";".join(f"{n}:{c}" for n, c in stats.counts)
            del hotel

            _, r_cur, r_peak = measure_memory(
                HotelSystem, N, V, 0, [], mode=RING, salt=str(salt))
            _, t_cur, t_peak = measure_memory(
                build_hotel_timed, N, V, K, RING, salt)

            add_row, remove_row = run_b_case(N, V, K, RING, salt)
            rows.append({
                "experiment": "C", "salt": str(salt), "N": N, "V": V, "K": K,
                "method": "ring", "ring_points": N * V,
                "guests_per_node": per_node,
                "max": stats.maximum, "min": stats.minimum,
                "mean": _r(stats.mean, 4), "std": _r(stats.std, 4),
                "cv": _r(stats.cv, 6),
                "t_build_ring_s": _r(t_ring), "t_place_guests_s": _r(t_place),
                "mem_ring_current_mib": _r(r_cur, 4), "mem_ring_peak_mib": _r(r_peak, 4),
                "mem_total_current_mib": _r(t_cur, 4), "mem_total_peak_mib": _r(t_peak, 4),
                "add_migrated": add_row["migrated_count"], "add_rate": add_row["migration_rate"],
                "remove_migrated": remove_row["migrated_count"],
                "remove_rate": remove_row["migration_rate"],
            })
    return rows


# ---------------------------------------------------------------- ไฟล์ประกอบ

def export_samples(out_dir):
    hotel = HotelSystem(3, 8, 3, [40, 30, 30], mode=RING, salt="0")
    n_guests = export_guests(hotel, os.path.join(out_dir, "sample_guests.csv"))
    report = hotel.add_node("4")
    n_moves = export_migrations(report, os.path.join(out_dir, "sample_migrations.csv"))
    return n_guests, n_moves


def write_run_info(out_dir, args_text):
    path = os.path.join(out_dir, "run_info.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"เวลาที่รัน   : {datetime.datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"Python        : {sys.version.split()[0]} ({platform.python_implementation()})\n")
        f.write(f"ระบบปฏิบัติการ : {platform.platform()}\n")
        f.write(f"โปรเซสเซอร์    : {platform.processor() or platform.machine()}\n")
        f.write(f"พารามิเตอร์    : {args_text}\n")
        f.write("หน่วยความจำ   : tracemalloc (เฉพาะส่วนที่ Python ติดตาม ไม่ใช่ทั้งโปรเซส)\n")
        f.write("ข้อความที่แฮช  : guest:{c}:{s} และ node:{node_id}:{j} นำหน้าด้วย salt\n")
        f.write("B: เพิ่มอาคารรหัส N+1, ลบอาคารรหัส (N+1)//2 ทั้งสองวิธี\n")


# ---------------------------------------------------------------- main

def main(argv=None):
    parser = argparse.ArgumentParser(description="รันการทดลอง A, B, C")
    parser.add_argument("-e", "--experiment", choices=["A", "B", "C", "all"], default="all")
    parser.add_argument("--salts", type=int, nargs="+", default=list(DEFAULT_SALTS))
    parser.add_argument("--out", default=RESULTS_DIR, help="โฟลเดอร์เก็บ CSV")
    parser.add_argument("--quick", action="store_true",
                        help="ขนาดเล็กเพื่อทดสอบสคริปต์ (ไม่ใช่ค่าจริงสำหรับรายงาน)")
    args = parser.parse_args(argv)

    if args.quick:
        a_ks, b_ns, b_k, c_k = [200, 1_000, 2_000], [5, 10, 20], 1_000, 1_000
    else:
        a_ks, b_ns, b_k, c_k = [1_000, 10_000, 100_000], [5, 10, 20], 10_000, 10_000

    todo = ["A", "B", "C"] if args.experiment == "all" else [args.experiment]
    os.makedirs(args.out, exist_ok=True)

    if "A" in todo:
        rows = run_experiment_a(a_ks, args.salts)
        write_csv(os.path.join(args.out, "experiment_A_results.csv"), FIELDS_A, rows)
    if "B" in todo:
        rows = run_experiment_b(b_ns, args.salts, K=b_k)
        write_csv(os.path.join(args.out, "experiment_B_results.csv"), FIELDS_B, rows)
    if "C" in todo:
        rows = run_experiment_c([1, 8, 32], args.salts, K=c_k)
        write_csv(os.path.join(args.out, "experiment_C_results.csv"), FIELDS_C, rows)

    export_samples(args.out)
    write_run_info(args.out, f"experiments={todo}, salts={args.salts}, quick={args.quick}")
    print(f"เสร็จแล้ว บันทึกที่ {args.out}")


if __name__ == "__main__":
    main()
