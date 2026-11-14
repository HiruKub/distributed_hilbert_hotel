"""ทดสอบ utils/ (reports, exporter, metrics) ตัวช่วยการทดลอง และเมนู CLI

รันจากโฟลเดอร์รากของโปรเจกต์:  python -m unittest tests.test_utils -v
"""
import contextlib
import csv
import io
import math
import os
import tempfile
import tracemalloc
import unittest
from types import SimpleNamespace
from unittest import mock

from cli.menu import HotelMenu
from core.hotel_system import HashType, HotelSystem
from experiments.run_experiments import NUM_CHANNELS, build_hotel_timed, channel_counts
from utils.exporter import (GUEST_FIELDS, MIGRATION_FIELDS, export_guests,
                            export_migrations, write_csv)
from utils.metrics import measure_memory, per_call_time, summarize, timed
from utils.reports import list_rooms, load_stats, node_sort_key, verify_consistency


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def stub_hotel(by_node, router_map):
    """โรงแรมจำลอง (ไม่ใช้ HotelSystem) สำหรับทดสอบ load_stats / verify_consistency"""
    by_id = {}
    for node, members in by_node.items():
        for key in members:
            by_id[key] = SimpleNamespace(node_id=node)
    return SimpleNamespace(
        guests_by_node=by_node, guests_by_id=by_id,
        router=SimpleNamespace(get_node=lambda c, s: router_map[(c, s)]))


# ------------------------------------------------------------------ เรียง node_id
class TestNodeSortKey(unittest.TestCase):
    def test_numeric_order_not_text_order(self):
        self.assertEqual(sorted(["1", "10", "2", "3"], key=node_sort_key), ["1", "2", "3", "10"])
        self.assertEqual(sorted(["12", "9", "100", "20"], key=node_sort_key), ["9", "12", "20", "100"])

    def test_non_numeric_after_numeric(self):
        self.assertEqual(sorted(["B", "10", "A", "2"], key=node_sort_key), ["2", "10", "A", "B"])


# ------------------------------------------------------------------ สถิติโหลด
class TestLoadStats(unittest.TestCase):
    def test_hand_computed_values(self):
        """3 อาคาร มีแขก 3, 0, 1 คน: mean = 4/3, std (ประชากร) = sqrt(14)/3, CV = sqrt(14)/4"""
        hotel = stub_hotel({"1": {(1, 1), (1, 2), (1, 3)}, "2": set(), "3": {(2, 1)}}, {})
        stats = load_stats(hotel)
        self.assertEqual(stats.counts, [("1", 3), ("2", 0), ("3", 1)])
        self.assertEqual((stats.total, stats.node_count, stats.maximum, stats.minimum), (4, 3, 3, 0))
        self.assertAlmostEqual(stats.mean, 4 / 3)
        self.assertAlmostEqual(stats.std, math.sqrt(14) / 3)
        self.assertAlmostEqual(stats.cv, math.sqrt(14) / 4)

    def test_includes_buildings_with_zero_guests(self):
        hotel = stub_hotel({"1": {(1, 1)}, "2": set(), "3": set()}, {})
        stats = load_stats(hotel)
        self.assertEqual(stats.node_count, 3)
        self.assertEqual(stats.minimum, 0)

    def test_no_guests_gives_zero_stats_and_no_cv(self):
        stats = load_stats(stub_hotel({"1": set(), "2": set()}, {}))
        self.assertEqual((stats.total, stats.maximum, stats.minimum, stats.mean, stats.std), (0, 0, 0, 0, 0))
        self.assertIsNone(stats.cv)
        self.assertEqual(stats.counts, [("1", 0), ("2", 0)])

    def test_perfectly_even_load_has_zero_cv(self):
        stats = load_stats(stub_hotel({"1": {(1, 1)}, "2": {(1, 2)}}, {}))
        self.assertEqual(stats.std, 0)
        self.assertEqual(stats.cv, 0)

    def test_buildings_listed_in_numeric_order(self):
        by_node = {str(i): set() for i in (10, 2, 1, 11, 3)}
        order = [n for n, _ in load_stats(stub_hotel(by_node, {})).counts]
        self.assertEqual(order, ["1", "2", "3", "10", "11"])

    def test_totals_match_real_hotel(self):
        hotel = HotelSystem(12, 8, 3, [40, 30, 20], salt="9")
        stats = load_stats(hotel)
        self.assertEqual(stats.total, 90)
        self.assertEqual(sum(c for _, c in stats.counts), 90)
        self.assertEqual(stats.node_count, 12)


# ------------------------------------------------------------------ รายการห้อง
class TestListRooms(unittest.TestCase):
    def test_sorted_by_node_then_numeric_room(self):
        hotel = HotelSystem(12, 8, 3, [40, 30, 20], salt="3")
        rows = list_rooms(hotel)
        self.assertEqual(len(rows), 90)
        keys = [(int(r.node_id), r.room_no) for r in rows]
        self.assertEqual(keys, sorted(keys))

    def test_node_10_after_node_2(self):
        hotel = HotelSystem(12, 8, 3, [60, 40, 20], salt="3")
        nodes_in_order = []
        for r in list_rooms(hotel):
            if not nodes_in_order or nodes_in_order[-1] != r.node_id:
                nodes_in_order.append(r.node_id)
        self.assertLess(nodes_in_order.index("2"), nodes_in_order.index("10"))

    def test_room_numbers_compared_as_numbers(self):
        """ห้อง 9 ต้องมาก่อนห้อง 10 ในอาคารเดียวกัน (ไม่ใช่เรียงเป็นข้อความ)"""
        hotel = HotelSystem(1, 4, 1, [30])
        rooms = [r.room_no for r in list_rooms(hotel)]
        self.assertEqual(rooms, sorted(rooms))
        self.assertTrue(any(r >= 10 for r in rooms) and any(r < 10 for r in rooms))

    def test_empty_hotel(self):
        self.assertEqual(list_rooms(HotelSystem(3, 8, 0, [])), [])


# ------------------------------------------------------------------ ตรวจดัชนี
class TestVerifyConsistency(unittest.TestCase):
    def test_consistent_real_hotels(self):
        for mode in (HashType.HASH_RING, HashType.HASH_MOD_N):
            hotel = HotelSystem(5, 8, 2, [30, 20], mode=mode, salt="a")
            self.assertEqual(verify_consistency(hotel), [])
            hotel.add_node("6")
            hotel.remove_node("2")
            self.assertEqual(verify_consistency(hotel), [])

    def test_clean_stub(self):
        hotel = stub_hotel({"1": {(1, 1)}, "2": {(1, 2)}}, {(1, 1): "1", (1, 2): "2"})
        self.assertEqual(verify_consistency(hotel), [])

    def test_detects_guest_missing_from_primary_index(self):
        hotel = stub_hotel({"1": {(1, 1)}, "2": set()}, {(1, 1): "1"})
        hotel.guests_by_node["2"].add((9, 9))
        self.assertTrue(verify_consistency(hotel))

    def test_detects_wrong_node_in_guest(self):
        hotel = stub_hotel({"1": {(1, 1)}, "2": set()}, {(1, 1): "1"})
        hotel.guests_by_id[(1, 1)].node_id = "2"
        self.assertTrue(verify_consistency(hotel))

    def test_detects_router_disagreement(self):
        hotel = stub_hotel({"1": {(1, 1)}, "2": set()}, {(1, 1): "2"})
        self.assertTrue(verify_consistency(hotel))

    def test_detects_count_mismatch(self):
        hotel = stub_hotel({"1": {(1, 1)}, "2": set()}, {(1, 1): "1", (5, 5): "1"})
        hotel.guests_by_id[(5, 5)] = SimpleNamespace(node_id="1")
        self.assertTrue(verify_consistency(hotel))


# ------------------------------------------------------------------ ส่งออก CSV
class TestExporter(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def path(self, name):
        return os.path.join(self.dir, name)

    def test_guest_csv_row_count_equals_guest_count(self):
        hotel = HotelSystem(5, 8, 3, [30, 20, 10], salt="1")
        for stage in ("เริ่มต้น", "หลังเพิ่มกลุ่ม", "หลังนำออก", "หลังเพิ่มอาคาร", "หลังลบอาคาร"):
            if stage == "หลังเพิ่มกลุ่ม":
                hotel.add_guest_group(4, 1, 15)
            elif stage == "หลังนำออก":
                hotel.remove_guest(1, 3)
                hotel.remove_guest(2, 5)
            elif stage == "หลังเพิ่มอาคาร":
                hotel.add_node("6")
            elif stage == "หลังลบอาคาร":
                hotel.remove_node("2")
            with self.subTest(stage=stage):
                p = self.path("guests.csv")
                written = export_guests(hotel, p)
                fields, rows = read_csv(p)
                self.assertEqual(written, len(hotel.guests_by_id))
                self.assertEqual(len(rows), len(hotel.guests_by_id))
                self.assertEqual(fields, GUEST_FIELDS)

    def test_guest_csv_columns_and_content(self):
        self.assertEqual(GUEST_FIELDS, ["channel_id", "sequence_id", "node_id", "room_no"])
        hotel = HotelSystem(4, 8, 2, [12, 8], salt="2")
        p = self.path("g.csv")
        export_guests(hotel, p)
        _, rows = read_csv(p)
        seen = set()
        for row in rows:
            c, s = int(row["channel_id"]), int(row["sequence_id"])
            seen.add((c, s))
            self.assertEqual(hotel.search_by_id(c, s), (row["node_id"], int(row["room_no"])))
        self.assertEqual(seen, set(hotel.guests_by_id))

    def test_guest_csv_order_is_node_then_room(self):
        hotel = HotelSystem(12, 8, 2, [40, 30], salt="2")
        p = self.path("g.csv")
        export_guests(hotel, p)
        _, rows = read_csv(p)
        keys = [(int(r["node_id"]), int(r["room_no"])) for r in rows]
        self.assertEqual(keys, sorted(keys))

    def test_guest_csv_empty_hotel_has_header_only(self):
        p = self.path("empty.csv")
        self.assertEqual(export_guests(HotelSystem(3, 8, 0, []), p), 0)
        fields, rows = read_csv(p)
        self.assertEqual(fields, GUEST_FIELDS)
        self.assertEqual(rows, [])

    def test_migration_csv_matches_report(self):
        hotel = HotelSystem(5, 8, 3, [60, 40, 20], mode=HashType.HASH_MOD_N, salt="5")
        report = hotel.add_node("6")
        p = self.path("m.csv")
        written = export_migrations(report, p)
        fields, rows = read_csv(p)
        self.assertEqual(fields, MIGRATION_FIELDS)
        self.assertEqual(written, report.migrated_count)
        self.assertEqual(len(rows), report.migrated_count)
        recorded = {(int(r["channel_id"]), int(r["sequence_id"])): (r["old_node"], r["new_node"], int(r["room_no"]))
                    for r in rows}
        for m in report.migrations:
            self.assertEqual(recorded[m.guest_id], (m.old_node, m.new_node, m.room_no))

    def test_migration_csv_empty_report(self):
        report = HotelSystem(3, 8, 0, []).add_node("4")
        p = self.path("m0.csv")
        self.assertEqual(export_migrations(report, p), 0)
        self.assertEqual(read_csv(p)[1], [])

    def test_write_csv_utf8_thai_and_creates_folder(self):
        p = os.path.join(self.dir, "sub", "folder", "thai.csv")
        write_csv(p, ["ชื่อ", "ค่า"], [{"ชื่อ": "อาคาร ๑", "ค่า": "ทดสอบ,จุลภาค"}])
        with open(p, "rb") as f:
            raw = f.read()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "ต้องไม่มี BOM (ค่าเริ่มต้น utf-8)")
        fields, rows = read_csv(p)
        self.assertEqual(fields, ["ชื่อ", "ค่า"])
        self.assertEqual(rows[0]["ค่า"], "ทดสอบ,จุลภาค")

    def test_write_csv_ignores_extra_keys_and_returns_count(self):
        p = self.path("x.csv")
        n = write_csv(p, ["a"], [{"a": 1, "zzz": 2}, {"a": 3}])
        self.assertEqual(n, 2)
        self.assertEqual([r["a"] for r in read_csv(p)[1]], ["1", "3"])


# ------------------------------------------------------------------ metrics
class TestMetrics(unittest.TestCase):
    def test_timed_returns_result_and_nonnegative_seconds(self):
        result, seconds = timed(lambda x, y=1: x + y, 2, y=3)
        self.assertEqual(result, 5)
        self.assertGreaterEqual(seconds, 0)

    def test_per_call_time_calls_every_item(self):
        calls = []
        avg = per_call_time(lambda a, b: calls.append((a, b)), [(1, 2), (3, 4), (5, 6)])
        self.assertEqual(calls, [(1, 2), (3, 4), (5, 6)])
        self.assertGreaterEqual(avg, 0)
        self.assertEqual(per_call_time(lambda: None, []), 0.0)

    def test_measure_memory(self):
        result, current, peak = measure_memory(lambda: [0] * 1_000_000)
        self.assertEqual(len(result), 1_000_000)
        self.assertGreater(current, 1.0)       # list ล้านช่องเกิน 1 MiB แน่นอน
        self.assertGreaterEqual(peak, current)
        self.assertFalse(tracemalloc.is_tracing(), "ต้องปิด tracemalloc หลังวัดเสร็จ")

    def test_summarize(self):
        s = summarize([3.0, 1.0, 2.0])
        self.assertEqual((s["min"], s["max"], s["median"]), (1.0, 3.0, 2.0))
        self.assertAlmostEqual(s["mean"], 2.0)
        self.assertEqual(summarize([])["mean"], 0.0)


# ------------------------------------------------------------------ ตัวช่วยการทดลอง
class TestExperimentHelpers(unittest.TestCase):
    def test_channel_counts_are_near_equal_and_sum_to_k(self):
        for k in (0, 7, 10, 1000, 10_003):
            counts = channel_counts(k)
            self.assertEqual(len(counts), NUM_CHANNELS)
            self.assertEqual(sum(counts), k)
            self.assertLessEqual(max(counts) - min(counts), 1)

    def test_build_hotel_timed(self):
        hotel, t_ring, t_place = build_hotel_timed(4, 8, 250, HashType.HASH_RING, 0)
        self.assertEqual(len(hotel.guests_by_id), 250)
        self.assertEqual(len(hotel.guests_by_node), 4)
        self.assertGreaterEqual(t_ring, 0)
        self.assertGreaterEqual(t_place, 0)
        self.assertEqual(verify_consistency(hotel), [])

    def test_same_salt_same_guests_between_methods(self):
        """เปรียบเทียบสองวิธีต้องใช้รหัสแขกชุดเดียวกัน"""
        ring, _, _ = build_hotel_timed(5, 8, 200, HashType.HASH_RING, 1)
        mod, _, _ = build_hotel_timed(5, 8, 200, HashType.HASH_MOD_N, 1)
        self.assertEqual(set(ring.guests_by_id), set(mod.guests_by_id))
        for key in ring.guests_by_id:
            self.assertEqual(ring.guests_by_id[key].room_no, mod.guests_by_id[key].room_no)


# ------------------------------------------------------------------ เมนู CLI
def run_menu(inputs):
    """รันเมนูด้วยอินพุตจำลอง อินพุตหมดแล้วจะเกิด EOF (โปรแกรมต้องออกอย่างสุภาพ)"""
    feed = iter(inputs)

    def fake_input(prompt=""):
        try:
            return next(feed)
        except StopIteration:
            raise EOFError

    menu = HotelMenu()
    out = io.StringIO()
    with mock.patch("builtins.input", fake_input), contextlib.redirect_stdout(out):
        menu.run()
    return menu, out.getvalue()


INIT_3_BUILDINGS = ["1", "3", "8", "2", "5 4", "", ""]   # N=3, V=8, C=2, [5,4], ring, salt "0"


class TestCliDoesNotCrash(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._cwd = os.getcwd()
        os.chdir(self._tmp.name)           # กันเมนูสร้างโฟลเดอร์ output ในโปรเจกต์
        self.addCleanup(os.chdir, self._cwd)

    def test_commands_before_init(self):
        for choice in ("2", "3", "4", "5", "6", "7", "10"):
            with self.subTest(choice=choice):
                menu, out = run_menu([choice, "0"])
                self.assertIsNone(menu.hotel)
                self.assertIn("ยังไม่ได้เริ่มระบบ", out)

    def test_invalid_menu_choices(self):
        menu, out = run_menu(["abc", "11", "-1", "", "0"])
        self.assertIn("ไม่มีเมนูนี้", out)

    def test_init_rejects_bad_numbers_then_accepts(self):
        inputs = ["1", "abc", "0", "3", "", "2", "5", "5 -1", "5 x", "5 4", "", "", "0"]
        menu, out = run_menu(inputs)
        self.assertIsNotNone(menu.hotel)
        self.assertEqual(len(menu.hotel.guests_by_node), 3)
        self.assertEqual(len(menu.hotel.guests_by_id), 9)
        self.assertIn("ต้องเป็นจำนวนเต็ม", out)

    def test_cancel_with_q(self):
        menu, out = run_menu(["1", "q", "0"])
        self.assertIsNone(menu.hotel)
        self.assertIn("ยกเลิก", out)

    def test_rejected_operations_keep_data(self):
        script = INIT_3_BUILDINGS + [
            "2", "2", "1", "1", "3",        # เพิ่มกลุ่มซ้ำ
            "2", "1", "1", "1",             # เพิ่มรายคนซ้ำ
            "3", "9", "9",                  # นำแขกที่ไม่มีอยู่ออก
            "5", "1", "9", "9",             # ค้นด้วยรหัสแขก ไม่พบ
            "5", "2", "1", "1000000",       # ค้นด้วยอาคาร+ห้อง ไม่พบ
            "4", "1", "1",                  # เพิ่มอาคารซ้ำ
            "4", "2", "99",                 # ลบอาคารที่ไม่มี
            "0"]
        menu, out = run_menu(script)
        self.assertEqual(len(menu.hotel.guests_by_id), 9)
        self.assertEqual(len(menu.hotel.guests_by_node), 3)
        self.assertEqual(verify_consistency(menu.hotel), [])
        self.assertGreaterEqual(out.count("ทำรายการไม่สำเร็จ"), 7)
        self.assertIn("ไม่พบ", out)

    def test_cannot_remove_last_building(self):
        script = ["1", "1", "8", "1", "5", "", "",   # N=1
                  "4", "2", "1",                      # ลบอาคารสุดท้าย
                  "0"]
        menu, out = run_menu(script)
        self.assertEqual(len(menu.hotel.guests_by_node), 1)
        self.assertEqual(len(menu.hotel.guests_by_id), 5)
        self.assertIn("ทำรายการไม่สำเร็จ", out)

    def test_normal_flow_add_remove_show_export(self):
        guests_csv = os.path.join(self._tmp.name, "guests.csv")
        moves_csv = os.path.join(self._tmp.name, "moves.csv")
        script = INIT_3_BUILDINGS + [
            "2", "2", "1", "6", "3",       # เพิ่มกลุ่ม c=1 s=6..8
            "2", "1", "5", "1",            # เพิ่มรายคนช่องทางใหม่ (5, 1)
            "3", "1", "1",                 # นำ (1,1) ออก
            "4", "1", "4", "5",            # เพิ่มอาคาร 4 แสดงรายการย้าย 5
            "6", "5",                      # แสดงห้อง 5 รายการ
            "7",                           # รายงานโหลด
            "10", guests_csv, moves_csv,
            "0"]
        menu, out = run_menu(script)
        k = len(menu.hotel.guests_by_id)
        self.assertEqual(k, 9 + 3 + 1 - 1)
        self.assertIn(f"แสดง 5 จาก {k}", out)
        self.assertIn("CV", out)
        self.assertIn("อัตราการย้าย", out)
        _, guest_rows = read_csv(guests_csv)
        self.assertEqual(len(guest_rows), k)
        _, move_rows = read_csv(moves_csv)
        self.assertEqual(len(move_rows), menu.last_report.migrated_count)

    def test_load_report_with_no_guests(self):
        menu, out = run_menu(["1", "2", "8", "0", "", "", "7", "0"])
        self.assertIn("ไม่คำนวณ", out)

    def test_export_without_migrations_is_graceful(self):
        p = os.path.join(self._tmp.name, "g.csv")
        menu, out = run_menu(INIT_3_BUILDINGS + ["10", p, "0"])
        self.assertTrue(os.path.exists(p))
        self.assertIn("ยังไม่มีรายการย้าย", out)

    def test_benchmark_and_compare_show_parameters(self):
        menu, out = run_menu(["8", "3", "4", "200", "0", "9", "5", "8", "300", "0", "0"])
        self.assertIn("N=3, V=4, K=200", out)
        self.assertIn("tracemalloc", out)
        self.assertIn("ring", out)
        self.assertIn("mod_n", out)

    def test_eof_exits_gracefully(self):
        menu, out = run_menu([])                      # EOF ทันที
        self.assertIn("ออกจากโปรแกรม", out)
        menu, out = run_menu(["1", "3"])              # EOF ระหว่างกรอก
        self.assertIn("ออกจากโปรแกรม", out)


if __name__ == "__main__":
    unittest.main()
