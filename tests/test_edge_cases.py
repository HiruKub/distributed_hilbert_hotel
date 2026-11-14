"""ทดสอบกรณีขอบ (โจทย์หัวข้อ 4.5) และกติกาการย้าย (หัวข้อ 4.4 / 9.2)

ทดสอบผ่าน HotelSystem เท่านั้น (พฤติกรรมที่เห็นจากภายนอก) ไม่ผูกกับโครงสร้างภายในของวงแหวน
จึงควรผ่านทั้งตอนวงแหวนเป็น list และเป็น tree

รันจากโฟลเดอร์รากของโปรเจกต์:  python -m unittest tests.test_edge_cases -v
"""
import os
import subprocess
import sys
import unittest

from core.hotel_system import HashType, HotelSystem
from utils.reports import list_rooms, load_stats, verify_consistency

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOTH_MODES = (HashType.HASH_RING, HashType.HASH_MOD_N)


def snapshot(hotel):
    """{(c, s): (node_id, room_no)}"""
    return {k: (g.node_id, g.room_no) for k, g in hotel.guests_by_id.items()}


def index_sizes(hotel):
    return len(hotel.guests_by_id), sum(len(m) for m in hotel.guests_by_node.values())


def make_hotel(mode=HashType.HASH_RING, N=5, V=8, counts=(60, 50, 40), salt="t"):
    return HotelSystem(N, V, len(counts), list(counts), mode=mode, salt=salt)


class HotelTestCase(unittest.TestCase):
    def assertUnchanged(self, hotel, before):
        self.assertEqual(snapshot(hotel), before, "ข้อมูลแขกต้องไม่เปลี่ยน")
        self.assertEqual(verify_consistency(hotel), [], "ดัชนีต้องสอดคล้องกัน")
        total, indexed = index_sizes(hotel)
        self.assertEqual(total, indexed)


# ------------------------------------------------------------------ การเริ่มระบบ
class TestInitValidation(unittest.TestCase):
    def test_needs_at_least_one_building(self):
        for n in (0, -1):
            with self.assertRaises(ValueError):
                HotelSystem(n, 8, 0, [])

    def test_channel_count_must_match_list(self):
        with self.assertRaises(ValueError):
            HotelSystem(3, 8, 2, [5])

    def test_negative_guest_count_rejected(self):
        with self.assertRaises(ValueError):
            HotelSystem(3, 8, 2, [5, -1])

    def test_ring_needs_positive_v(self):
        with self.assertRaises(ValueError):
            HotelSystem(3, 0, 1, [5], mode=HashType.HASH_RING)

    def test_initial_guest_total_and_sequence_starts_at_one(self):
        hotel = make_hotel(counts=(7, 0, 3))
        self.assertEqual(len(hotel.guests_by_id), 10)
        self.assertIn((1, 1), hotel.guests_by_id)
        self.assertIn((1, 7), hotel.guests_by_id)
        self.assertNotIn((2, 1), hotel.guests_by_id)
        self.assertIn((3, 3), hotel.guests_by_id)

    def test_empty_hotel_can_be_created(self):
        """C = 0 และ s = [] ต้องใช้ได้ (สคริปต์ทดลองสร้างโรงแรมเปล่าด้วยวิธีนี้เพื่อแยกเวลา)"""
        hotel = HotelSystem(4, 8, 0, [])
        self.assertEqual(len(hotel.guests_by_id), 0)
        self.assertEqual(len(hotel.guests_by_node), 4)


# ------------------------------------------------------------------ รหัสแขกซ้ำ
class TestDuplicateGuests(HotelTestCase):
    def test_duplicate_single_guest_rejected(self):
        for mode in BOTH_MODES:
            with self.subTest(mode=mode):
                hotel = make_hotel(mode)
                before = snapshot(hotel)
                with self.assertRaises(ValueError):
                    hotel.add_guest(1, 5)
                self.assertUnchanged(hotel, before)

    def test_group_overlapping_partially_rejects_whole_group(self):
        """กลุ่มที่ซ้ำเพียงบางรายการ ต้องปฏิเสธทั้งกลุ่ม ไม่เพิ่มรายการที่ไม่ซ้ำ"""
        hotel = make_hotel(counts=(10, 5))
        before = snapshot(hotel)
        with self.assertRaises(ValueError):
            hotel.add_guest_group(1, 8, 5)  # 8..12 ซ้ำที่ 8, 9, 10
        self.assertNotIn((1, 11), hotel.guests_by_id)
        self.assertNotIn((1, 12), hotel.guests_by_id)
        self.assertUnchanged(hotel, before)

    def test_group_count_zero_changes_nothing(self):
        hotel = make_hotel()
        before = snapshot(hotel)
        self.assertTrue(hotel.add_guest_group(1, 1, 0))
        self.assertTrue(hotel.add_guest_group(9, 1, 0))
        self.assertUnchanged(hotel, before)

    def test_group_invalid_arguments(self):
        hotel = make_hotel()
        before = snapshot(hotel)
        for args in [(1, 1, -1), (0, 1, 3), (1, 0, 3), ("a", 1, 3), (1, "a", 3), (1, 1, 2.5)]:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    hotel.add_guest_group(*args)
        self.assertUnchanged(hotel, before)

    def test_single_guest_invalid_code_rejected(self):
        hotel = make_hotel()
        before = snapshot(hotel)
        for c, s in [(0, 1), (1, 0), (-2, 3), ("x", 1), (1.5, 2)]:
            with self.subTest(c=c, s=s):
                with self.assertRaises((ValueError, TypeError)):
                    hotel.add_guest(c, s)
        self.assertUnchanged(hotel, before)

    def test_new_group_in_new_channel_and_existing_channel(self):
        hotel = make_hotel(counts=(5, 5))
        hotel.add_guest_group(1, 6, 4)   # ช่องทางเดิมต่อท้าย
        hotel.add_guest_group(7, 1, 3)   # ช่องทางใหม่
        self.assertEqual(len(hotel.guests_by_id), 17)
        self.assertEqual(verify_consistency(hotel), [])


# ------------------------------------------------------------------ นำแขกออก
class TestRemoveGuest(HotelTestCase):
    def test_remove_missing_guest_changes_nothing(self):
        hotel = make_hotel()
        before = snapshot(hotel)
        for c, s in [(9, 9), (1, 999), (3, 41)]:
            with self.subTest(c=c, s=s):
                with self.assertRaises(ValueError):
                    hotel.remove_guest(c, s)
        self.assertUnchanged(hotel, before)

    def test_remove_then_stats_follow(self):
        hotel = make_hotel(counts=(10,))
        hotel.remove_guest(1, 4)
        self.assertEqual(len(hotel.guests_by_id), 9)
        self.assertEqual(load_stats(hotel).total, 9)
        with self.assertRaises(ValueError):
            hotel.search_by_id(1, 4)
        self.assertEqual(verify_consistency(hotel), [])

    def test_readd_after_remove_is_new_stay_computed_from_current_ring(self):
        hotel = make_hotel()
        hotel.add_node("6")
        node_before, room_before = hotel.search_by_id(2, 7)
        hotel.remove_guest(2, 7)
        hotel.add_guest(2, 7)
        node_after, room_after = hotel.search_by_id(2, 7)
        self.assertEqual(node_after, hotel.router.get_node(2, 7))
        self.assertEqual(node_after, node_before)
        self.assertEqual(room_after, room_before)
        self.assertEqual(verify_consistency(hotel), [])


# ------------------------------------------------------------------ ค้นหาไม่พบ
class TestSearchNotFound(HotelTestCase):
    def test_search_by_id_not_found(self):
        hotel = make_hotel()
        for c, s in [(9, 9), (1, 61)]:
            with self.assertRaises(ValueError):
                hotel.search_by_id(c, s)

    def test_search_by_id_invalid_code(self):
        hotel = make_hotel()
        for c, s in [(0, 1), (1, 0), (-1, -1)]:
            with self.assertRaises(ValueError):
                hotel.search_by_id(c, s)

    def test_search_by_node_room_not_found(self):
        hotel = make_hotel()
        node, room = hotel.search_by_id(1, 1)
        other = next(n for n in hotel.guests_by_node if n != node)
        with self.assertRaises(ValueError):
            hotel.search_by_node_room(other, room)       # ห้องมีจริง แต่อยู่อาคารอื่น
        with self.assertRaises(ValueError):
            hotel.search_by_node_room("999", room)       # ไม่มีอาคารนี้
        with self.assertRaises(ValueError):
            hotel.search_by_node_room(node, 10 ** 9)     # ไม่มีแขกที่ห้องนี้

    def test_search_by_node_room_nonpositive_room(self):
        hotel = make_hotel()
        node = next(iter(hotel.guests_by_node))
        for room in (0, -5):
            with self.assertRaises(ValueError):
                hotel.search_by_node_room(node, room)


# ------------------------------------------------------------------ อาคาร
class TestBuildingEdgeCases(HotelTestCase):
    def test_add_existing_building_rejected_and_ring_not_polluted(self):
        """เพิ่มรหัสอาคารซ้ำ: ปฏิเสธ และลบทีหลังต้องลบออกหมด ไม่มีแขกเหลือที่อาคารนั้น"""
        hotel = make_hotel()
        hotel.add_node("6")
        before = snapshot(hotel)
        with self.assertRaises(ValueError):
            hotel.add_node("6")
        self.assertUnchanged(hotel, before)

        hotel.remove_node("6")
        self.assertNotIn("6", hotel.guests_by_node)
        for (c, s), guest in hotel.guests_by_id.items():
            self.assertNotEqual(guest.node_id, "6")
            self.assertNotEqual(hotel.router.get_node(c, s), "6")
        self.assertEqual(verify_consistency(hotel), [])

    def test_add_existing_initial_building_rejected(self):
        hotel = make_hotel()
        before = snapshot(hotel)
        with self.assertRaises(ValueError):
            hotel.add_node("1")
        self.assertUnchanged(hotel, before)

    def test_remove_missing_building_changes_nothing(self):
        for mode in BOTH_MODES:
            with self.subTest(mode=mode):
                hotel = make_hotel(mode)
                before = snapshot(hotel)
                with self.assertRaises(ValueError):
                    hotel.remove_node("99")
                self.assertUnchanged(hotel, before)
                self.assertEqual(len(hotel.guests_by_node), 5)

    def test_cannot_remove_last_building_even_when_empty(self):
        for mode in BOTH_MODES:
            for counts in ((12,), (0,)):
                with self.subTest(mode=mode, counts=counts):
                    hotel = HotelSystem(1, 8, 1, list(counts), mode=mode, salt="x")
                    before = snapshot(hotel)
                    with self.assertRaises(ValueError):
                        hotel.remove_node("1")
                    self.assertUnchanged(hotel, before)
                    self.assertEqual(list(hotel.guests_by_node), ["1"])
                    if counts[0]:
                        self.assertEqual(hotel.search_by_id(1, 1)[0], "1")  # ยังค้นหาได้

    def test_can_remove_down_to_one_then_refuse(self):
        hotel = HotelSystem(2, 8, 1, [20], salt="y")
        hotel.remove_node("1")
        self.assertEqual(len(hotel.guests_by_id), 20)
        with self.assertRaises(ValueError):
            hotel.remove_node("2")
        self.assertEqual(verify_consistency(hotel), [])


# ------------------------------------------------------------------ ไม่มีแขก K = 0
class TestEmptySystem(HotelTestCase):
    def test_migration_report_with_no_guests(self):
        for mode in BOTH_MODES:
            with self.subTest(mode=mode):
                hotel = HotelSystem(3, 8, 0, [], mode=mode)
                add_report = hotel.add_node("4")
                self.assertEqual(add_report.migrated_count, 0)
                self.assertEqual(add_report.total_guests_k, 0)
                self.assertEqual(add_report.migration_rate, 0.0)
                self.assertIn("ไม่คำนวณ", add_report.rate_status)
                remove_report = hotel.remove_node("2")
                self.assertEqual(remove_report.migrated_count, 0)
                self.assertIn("ไม่คำนวณ", remove_report.rate_status)

    def test_stats_and_listing_with_no_guests(self):
        hotel = HotelSystem(3, 8, 2, [0, 0])
        stats = load_stats(hotel)
        self.assertEqual((stats.total, stats.maximum, stats.minimum, stats.mean, stats.std), (0, 0, 0, 0, 0))
        self.assertIsNone(stats.cv)
        self.assertEqual(stats.node_count, 3)
        self.assertEqual(list_rooms(hotel), [])

    def test_search_on_empty_system(self):
        hotel = HotelSystem(3, 8, 0, [])
        with self.assertRaises(ValueError):
            hotel.search_by_id(1, 1)
        with self.assertRaises(ValueError):
            hotel.search_by_node_room("1", 1)


# ------------------------------------------------------------------ กติกาการย้าย (9.2 ข้อ 1 และ 5)
class TestAddressesStable(HotelTestCase):
    def test_adding_guests_never_moves_existing_guests(self):
        for mode in BOTH_MODES:
            with self.subTest(mode=mode):
                hotel = make_hotel(mode)
                before = snapshot(hotel)
                hotel.add_guest_group(1, 61, 25)   # ช่องทางเดิม
                hotel.add_guest_group(8, 1, 30)    # ช่องทางใหม่
                hotel.add_guest(2, 51)
                after = snapshot(hotel)
                for key, address in before.items():
                    self.assertEqual(after[key], address, f"แขก {key} ย้ายห้อง")
                self.assertEqual(len(after), len(before) + 25 + 30 + 1)
                self.assertEqual(verify_consistency(hotel), [])


class TestMigrationRules(HotelTestCase):
    def check_report_matches_reality(self, hotel, report, before, after):
        changed = {k for k in before if before[k][0] != after[k][0]}
        self.assertEqual({m.guest_id for m in report.migrations}, changed)
        self.assertEqual(report.migrated_count, len(report.migrations))
        self.assertEqual(report.migrated_count, len(changed))
        self.assertEqual(report.total_guests_k, len(before))
        self.assertEqual(len(after), len(before), "จำนวนแขกรวมต้องไม่หายไม่เพิ่ม")
        for m in report.migrations:
            self.assertEqual(m.old_node, before[m.guest_id][0])
            self.assertEqual(m.new_node, after[m.guest_id][0])
            self.assertEqual(m.room_no, before[m.guest_id][1])
        for key in before:  # room_no ต้องคงเดิม เปลี่ยนเฉพาะ node_id
            self.assertEqual(before[key][1], after[key][1])
        self.assertEqual(verify_consistency(hotel), [])
        return changed

    def test_add_building_ring(self):
        for v in (1, 8, 32):
            with self.subTest(V=v):
                hotel = make_hotel(V=v, counts=(150, 100, 50))
                before = snapshot(hotel)
                report = hotel.add_node("6")
                after = snapshot(hotel)
                changed = self.check_report_matches_reality(hotel, report, before, after)
                for m in report.migrations:
                    self.assertEqual(m.new_node, "6", "ผู้ย้ายต้องเข้าอาคารใหม่เท่านั้น")
                self.assertEqual(hotel.guests_by_node["6"], changed)

    def test_remove_building_ring(self):
        for v in (1, 8, 32):
            with self.subTest(V=v):
                hotel = make_hotel(V=v, counts=(150, 100, 50))
                before = snapshot(hotel)
                leaving = {k for k, (node, _) in before.items() if node == "3"}
                report = hotel.remove_node("3")
                after = snapshot(hotel)
                changed = self.check_report_matches_reality(hotel, report, before, after)
                self.assertEqual(changed, leaving, "ต้องย้ายเฉพาะแขกของอาคารที่ถูกลบ")
                for key, (node, _) in before.items():
                    if node != "3":
                        self.assertEqual(after[key][0], node, "แขกอาคารอื่นห้ามขยับ")
                self.assertNotIn("3", hotel.guests_by_node)

    def test_report_matches_reality_for_mod_n(self):
        hotel = make_hotel(HashType.HASH_MOD_N, counts=(150, 100, 50))
        before = snapshot(hotel)
        report = hotel.add_node("6")
        self.check_report_matches_reality(hotel, report, before, snapshot(hotel))
        before = snapshot(hotel)
        report = hotel.remove_node("2")
        self.check_report_matches_reality(hotel, report, before, snapshot(hotel))

    def test_printed_migration_lines_equal_reported_count(self):
        hotel = make_hotel(HashType.HASH_MOD_N, counts=(150, 100, 50))
        report = hotel.add_node("6")
        self.assertGreater(report.migrated_count, 0)
        text = report.generate_summary()
        self.assertEqual(text.count("รหัสแขก ("), report.migrated_count)

    def test_search_still_correct_after_guest_moves(self):
        """ตัวอย่างที่ข้อมูลหลายส่วนต้องสอดคล้อง: แขกย้ายอาคารแล้วดัชนีทั้งสองทางยังตอบถูก"""
        hotel = make_hotel(counts=(150, 100, 50))
        report = hotel.add_node("6")
        self.assertGreater(report.migrated_count, 0)
        for m in report.migrations:
            c, s = m.guest_id
            self.assertEqual(hotel.search_by_id(c, s), ("6", m.room_no))
            self.assertEqual(hotel.search_by_node_room("6", m.room_no), (c, s))
            with self.assertRaises(ValueError):
                hotel.search_by_node_room(m.old_node, m.room_no)


# ------------------------------------------------------------------ เทียบกับตัวเฉลยตามกติกาโจทย์ 4.3
def oracle_node(node_ids, v, salt, c, s):
    """เขียนกติกาวงแหวนตรง ๆ แบบไม่พึ่งโค้ดของทีม (ค้นเชิงเส้น ไม่ใช้ bisect/tree)

    - จุดอาคาร: hash64(salt + "node:{id}:{j}") โดย j = 0..V-1
    - ตำแหน่งแขก: hash64(salt + "guest:{c}:{s}")
    - เรียงจุดด้วย (ตำแหน่ง, node_id, j) เลือกจุดแรกที่ตำแหน่ง >= แขก ไม่มีให้วนไปจุดแรก
    """
    from core.hash_ring import hash64
    points = sorted((hash64(f"{salt}node:{n}:{j}"), n, j) for n in node_ids for j in range(v))
    position = hash64(f"{salt}guest:{c}:{s}")
    for point_position, node_id, _ in points:
        if point_position >= position:
            return node_id
    return points[0][1]


class TestRingMatchesSpecOracle(unittest.TestCase):
    """ทดสอบกติกา 4.3 จากผลลัพธ์จริงของ HotelSystem (ใช้ได้ทั้งวงแหวนแบบ list และ tree)

    ถ้าทีมเปลี่ยนรูปแบบข้อความที่แฮช (guest:c:s / node:id:j) ต้องแก้ oracle_node ให้ตรงกัน
    """

    def assertMatchesOracle(self, hotel, v, salt):
        nodes = list(hotel.guests_by_node)
        for (c, s), guest in hotel.guests_by_id.items():
            self.assertEqual(guest.node_id, oracle_node(nodes, v, salt, c, s), f"แขก {(c, s)}")
            self.assertEqual(hotel.router.get_node(c, s), guest.node_id)

    def test_initial_placement(self):
        for v in (1, 8, 32):
            for salt in ("0", "1", "xyz"):
                with self.subTest(V=v, salt=salt):
                    hotel = HotelSystem(5, v, 3, [80, 50, 30], salt=salt)
                    self.assertMatchesOracle(hotel, v, salt)

    def test_placement_after_adding_and_removing_buildings(self):
        for v in (1, 8):
            with self.subTest(V=v):
                hotel = HotelSystem(5, v, 3, [80, 50, 30], salt="q")
                hotel.add_node("6")
                self.assertMatchesOracle(hotel, v, "q")
                hotel.remove_node("2")
                self.assertMatchesOracle(hotel, v, "q")
                hotel.add_node("10")
                self.assertMatchesOracle(hotel, v, "q")

    def test_guests_added_later_follow_the_same_rule(self):
        hotel = HotelSystem(4, 8, 1, [20], salt="late")
        hotel.add_node("5")
        hotel.add_guest_group(1, 21, 30)
        hotel.add_guest_group(6, 1, 30)
        self.assertMatchesOracle(hotel, 8, "late")


class TestModNMatchesSpecOracle(unittest.TestCase):
    """hash mod N (โจทย์หัวข้อ 7.1): เก็บรหัสอาคารตามลำดับที่เพิ่ม เลือกที่ดัชนี H(guest) mod N
    เพิ่มแล้วต่อท้าย ลบแล้วเอาออกโดยรักษาลำดับที่เหลือ"""

    def assertMatchesOracle(self, hotel, order, salt):
        from core.hash_ring import hash64
        for (c, s), guest in hotel.guests_by_id.items():
            expected = order[hash64(f"{salt}guest:{c}:{s}") % len(order)]
            self.assertEqual(guest.node_id, expected, f"แขก {(c, s)}")

    def test_placement_follows_insertion_order_rule(self):
        for salt in ("0", "1"):
            with self.subTest(salt=salt):
                hotel = HotelSystem(5, 8, 3, [80, 50, 30], mode=HashType.HASH_MOD_N, salt=salt)
                order = ["1", "2", "3", "4", "5"]
                self.assertMatchesOracle(hotel, order, salt)
                hotel.add_node("6")
                order.append("6")
                self.assertMatchesOracle(hotel, order, salt)
                hotel.remove_node("2")
                order.remove("2")
                self.assertMatchesOracle(hotel, order, salt)
                hotel.add_node("10")
                order.append("10")
                self.assertMatchesOracle(hotel, order, salt)


# ------------------------------------------------------------------ แฮชคงที่ข้ามการรัน
class TestHashStability(unittest.TestCase):
    EXPECTED = {
        "guest:1:1": 3062031282815716176,
        "node:1:0": 3505680375118999729,
        "0guest:1:1": 11620069146110160878,
    }

    def test_fixed_values(self):
        from core.hash_ring import hash64
        for text, value in self.EXPECTED.items():
            self.assertEqual(hash64(text), value)

    def test_same_value_in_fresh_processes_with_different_python_hash_seeds(self):
        """ปิดโปรแกรมแล้วเปิดใหม่ค่าแฮชต้องเหมือนเดิม (ไม่ได้ใช้ hash() ของ Python)"""
        code = "from core.hash_ring import hash64; print(hash64('guest:1:1'))"
        seen = set()
        for seed in ("0", "1", "12345"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                                 capture_output=True, text=True, check=True).stdout.strip()
            seen.add(out)
        self.assertEqual(seen, {str(self.EXPECTED["guest:1:1"])})

    def test_same_guests_same_buildings_across_two_runs(self):
        a = snapshot(make_hotel(salt="same"))
        b = snapshot(make_hotel(salt="same"))
        self.assertEqual(a, b)

    def test_salt_changes_placement_but_not_rooms(self):
        a = snapshot(make_hotel(salt="0", counts=(200,)))
        b = snapshot(make_hotel(salt="1", counts=(200,)))
        self.assertNotEqual({k: v[0] for k, v in a.items()}, {k: v[0] for k, v in b.items()})
        self.assertEqual({k: v[1] for k, v in a.items()}, {k: v[1] for k, v in b.items()})


if __name__ == "__main__":
    unittest.main()
