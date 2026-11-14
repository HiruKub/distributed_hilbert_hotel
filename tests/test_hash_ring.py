"""ทดสอบวงแหวน (HashRing) ตามโจทย์หัวข้อ 4.3, 9.1 และ 9.2 ข้อ 4-5

รันจากโฟลเดอร์รากของโปรเจกต์:  python -m unittest tests.test_hash_ring -v
"""
import unittest
from unittest import mock

from core.hash_ring import HashRing, hash64
from core.hotel_system import HotelSystem
from utils.reports import verify_consistency

RING_MAX = 2 ** 64 - 1


def fixed_hash(table):
    """สร้างฟังก์ชันแทน hash64 ที่คืนตำแหน่งที่กำหนดไว้ล่วงหน้า (ใช้ตรวจตรรกะเท่านั้น)"""
    def fake(text):
        return table[text]
    return fake


def make_ring(points):
    """points = {node_id: [pos_j0, pos_j1, ...]} สร้างวงแหวนด้วยตำแหน่งที่กำหนดเอง"""
    table = {f"node:{n}:{j}": p for n, ps in points.items() for j, p in enumerate(ps)}
    v = max(len(ps) for ps in points.values())
    with mock.patch("core.hash_ring.hash64", fixed_hash(table)):
        ring = HashRing(v)
        for n in points:
            ring.add_node(n)
    return ring


# ------------------------------------------------------------------ hash64
class TestHash64(unittest.TestCase):
    def test_range_and_type(self):
        for text in ("guest:1:1", "node:1:0", "", "ไทย"):
            value = hash64(text)
            self.assertIsInstance(value, int)
            self.assertTrue(0 <= value <= RING_MAX)

    def test_deterministic(self):
        self.assertEqual(hash64("guest:3:4"), hash64("guest:3:4"))
        self.assertNotEqual(hash64("guest:3:4"), hash64("guest:4:3"))

    def test_guest_and_node_texts_are_separate(self):
        self.assertNotEqual(hash64("guest:1:1"), hash64("node:1:1"))


# ------------------------------------------------------------------ การเลือกอาคารบนวงแหวน
class TestLookupRule(unittest.TestCase):
    """วงแหวนเล็กตามโจทย์ 9.1: A@20, B@50, C@80 กติกา >= และวนกลับต้นวงแหวน"""

    def setUp(self):
        self.ring = make_ring({"A": [20], "B": [50], "C": [80]})

    def test_table_from_spec(self):
        expected = {10: "A", 20: "A", 25: "B", 35: "B", 50: "B", 70: "C", 90: "A"}
        for position, node in expected.items():
            with self.subTest(position=position):
                self.assertEqual(self.ring.get_node_by_position(position), node)

    def test_exactly_on_point_belongs_to_that_point(self):
        for position, node in ((20, "A"), (50, "B"), (80, "C")):
            self.assertEqual(self.ring.get_node_by_position(position), node)

    def test_between_points_goes_clockwise_to_next(self):
        self.assertEqual(self.ring.get_node_by_position(21), "B")
        self.assertEqual(self.ring.get_node_by_position(51), "C")
        self.assertEqual(self.ring.get_node_by_position(81 - 1), "C")

    def test_wrap_around_after_last_point(self):
        self.assertEqual(self.ring.get_node_by_position(81), "A")
        self.assertEqual(self.ring.get_node_by_position(RING_MAX), "A")

    def test_position_zero(self):
        self.assertEqual(self.ring.get_node_by_position(0), "A")

    def test_empty_ring_returns_none(self):
        ring = HashRing(4)
        self.assertIsNone(ring.get_node_by_position(5))
        self.assertIsNone(ring.get_node(1, 1))


# ------------------------------------------------------------------ จุดชนกัน
class TestCollisions(unittest.TestCase):
    def test_colliding_points_all_kept_and_ordered(self):
        ring = make_ring({"B": [40, 70], "A": [40, 90]})
        self.assertEqual(ring.point_count, 4)
        self.assertEqual(ring._ring, [(40, "A", 0), (40, "B", 0), (70, "B", 1), (90, "A", 1)])

    def test_guest_on_colliding_position_uses_first_by_key(self):
        ring = make_ring({"B": [40], "A": [40]})
        self.assertEqual(ring.get_node_by_position(40), "A")
        self.assertEqual(ring.get_node_by_position(39), "A")

    def test_same_node_collision_ordered_by_j(self):
        ring = make_ring({"A": [40, 40]})
        self.assertEqual(ring._ring, [(40, "A", 0), (40, "A", 1)])
        self.assertEqual(ring.get_node_by_position(40), "A")

    def test_removing_one_colliding_node_keeps_the_other(self):
        ring = make_ring({"B": [40], "A": [40], "C": [90]})
        ring.remove_node("A")
        self.assertEqual(ring.get_node_by_position(40), "B")
        self.assertEqual(ring.point_count, 2)

    def test_guests_on_same_position_get_different_rooms(self):
        table = {"node:1:0": 50, "node:2:0": 90, "guest:1:1": 30, "guest:1:2": 30, "guest:2:1": 30}
        with mock.patch("core.hash_ring.hash64", fixed_hash(table)):
            hotel = HotelSystem(2, 1, 2, [2, 1])
        nodes = {hotel.search_by_id(c, s)[0] for c, s in hotel.guests_by_id}
        self.assertEqual(nodes, {"1"})
        rooms = [g.room_no for g in hotel.guests_by_id.values()]
        self.assertEqual(len(rooms), len(set(rooms)))
        self.assertEqual(len(rooms), 3)


# ------------------------------------------------------------------ ตัวอย่าง 9.1 ผ่าน HotelSystem
class TestSpecExample91(unittest.TestCase):
    POSITIONS = [10, 20, 25, 35, 50, 70, 90]

    def build(self):
        table = {"node:1:0": 20, "node:2:0": 50, "node:3:0": 80, "node:4:0": 35}
        table.update({f"guest:1:{i + 1}": p for i, p in enumerate(self.POSITIONS)})
        return table

    def owners(self, hotel):
        return {self.POSITIONS[s - 1]: g.node_id for (c, s), g in hotel.guests_by_id.items()}

    def test_initial_state(self):
        with mock.patch("core.hash_ring.hash64", fixed_hash(self.build())):
            hotel = HotelSystem(3, 1, 1, [7])
            self.assertEqual(self.owners(hotel),
                             {10: "1", 20: "1", 25: "2", 35: "2", 50: "2", 70: "3", 90: "1"})

    def test_add_d_moves_two_guests_into_d_only(self):
        with mock.patch("core.hash_ring.hash64", fixed_hash(self.build())):
            hotel = HotelSystem(3, 1, 1, [7])
            before = {k: g.room_no for k, g in hotel.guests_by_id.items()}
            report = hotel.add_node("4")
            self.assertEqual(report.migrated_count, 2)
            self.assertEqual({m.new_node for m in report.migrations}, {"4"})
            self.assertEqual(sorted(self.POSITIONS[m.guest_id[1] - 1] for m in report.migrations), [25, 35])
            for m in report.migrations:
                self.assertEqual(m.room_no, before[m.guest_id])
            self.assertEqual(self.owners(hotel),
                             {10: "1", 20: "1", 25: "4", 35: "4", 50: "2", 70: "3", 90: "1"})
            self.assertEqual(verify_consistency(hotel), [])

    def test_remove_b_moves_three_guests_to_c(self):
        with mock.patch("core.hash_ring.hash64", fixed_hash(self.build())):
            hotel = HotelSystem(3, 1, 1, [7])
            before = {k: g.room_no for k, g in hotel.guests_by_id.items()}
            report = hotel.remove_node("2")
            self.assertEqual(report.migrated_count, 3)
            self.assertEqual({(m.old_node, m.new_node) for m in report.migrations}, {("2", "3")})
            self.assertEqual(sorted(self.POSITIONS[m.guest_id[1] - 1] for m in report.migrations), [25, 35, 50])
            for m in report.migrations:
                self.assertEqual(m.room_no, before[m.guest_id])
            self.assertEqual(self.owners(hotel),
                             {10: "1", 20: "1", 25: "3", 35: "3", 50: "3", 70: "3", 90: "1"})
            self.assertEqual(verify_consistency(hotel), [])

    def test_guest_at_90_wraps_to_a(self):
        with mock.patch("core.hash_ring.hash64", fixed_hash(self.build())):
            hotel = HotelSystem(3, 1, 1, [7])
            self.assertEqual(hotel.search_by_id(1, 7)[0], "1")


# ------------------------------------------------------------------ จัดการอาคารบนวงแหวน (V > 1)
class TestRingMembership(unittest.TestCase):
    def test_point_count_is_n_times_v(self):
        for n, v in ((1, 1), (3, 8), (10, 32)):
            ring = HashRing(v, "s")
            for i in range(1, n + 1):
                ring.add_node(str(i))
            self.assertEqual(ring.point_count, n * v)
            self.assertEqual(ring.node_count, n)

    def test_ring_is_sorted(self):
        ring = HashRing(16, "s")
        for i in range(1, 6):
            ring.add_node(str(i))
        self.assertEqual(ring._ring, sorted(ring._ring))

    def test_add_existing_node_rejected_and_not_duplicated(self):
        ring = HashRing(8, "s")
        self.assertTrue(ring.add_node("1"))
        snapshot = list(ring._ring)
        self.assertFalse(ring.add_node("1"))
        self.assertEqual(ring._ring, snapshot)

    def test_add_node_keeps_existing_points_unchanged(self):
        ring = HashRing(8, "s")
        for i in range(1, 4):
            ring.add_node(str(i))
        before = set(ring._ring)
        ring.add_node("4")
        after = set(ring._ring)
        self.assertTrue(before <= after)
        self.assertEqual({p[1] for p in after - before}, {"4"})
        self.assertEqual(len(after - before), 8)

    def test_remove_node_removes_all_its_points_only(self):
        ring = HashRing(8, "s")
        for i in range(1, 5):
            ring.add_node(str(i))
        others = [p for p in ring._ring if p[1] != "3"]
        self.assertTrue(ring.remove_node("3"))
        self.assertEqual(ring._ring, others)
        self.assertEqual(ring.get_points("3"), [])
        self.assertNotIn("3", ring)

    def test_remove_missing_and_last_node_rejected(self):
        ring = HashRing(4, "s")
        ring.add_node("1")
        self.assertFalse(ring.remove_node("99"))
        self.assertFalse(ring.remove_node("1"))
        self.assertEqual(ring.point_count, 4)
        self.assertEqual(ring.node_count, 1)
        self.assertIsNotNone(ring.get_node(1, 1))

    def test_invalid_v_rejected(self):
        for bad in (0, -1, True, 1.5, "8", None):
            with self.subTest(v=bad):
                with self.assertRaises(ValueError):
                    HashRing(bad)

    def test_text_formats_are_separated_and_salted(self):
        ring = HashRing(2, "S")
        self.assertEqual(ring._node_position("7", 1), hash64("Snode:7:1"))
        self.assertEqual(ring._guest_position(2, 5), hash64("Sguest:2:5"))

    def test_lookup_independent_of_insertion_order(self):
        a, b = HashRing(8, "s"), HashRing(8, "s")
        for i in ("1", "2", "3", "4"):
            a.add_node(i)
        for i in ("4", "2", "1", "3"):
            b.add_node(i)
        self.assertEqual(a._ring, b._ring)
        for c in range(1, 6):
            for s in range(1, 30):
                self.assertEqual(a.get_node(c, s), b.get_node(c, s))


if __name__ == "__main__":
    unittest.main()