"""ทดสอบเลขห้อง (Cantor pairing) และคลาส Guest

รันจากโฟลเดอร์รากของโปรเจกต์:  python -m unittest tests.test_cantor -v
"""
import unittest
from math import comb

from core.guest import Guest
from core.hotel_system import HotelSystem


class TestCantorFormula(unittest.TestCase):
    def test_examples_from_spec(self):
        """ตารางตัวอย่างในโจทย์หัวข้อ 4.2"""
        table = {(1, 1): 1, (2, 1): 2, (1, 2): 3, (3, 1): 4, (2, 2): 5}
        for (c, s), room in table.items():
            with self.subTest(guest=(c, s)):
                self.assertEqual(Guest.calculate_room_no(c, s), room)
                self.assertEqual(Guest(c, s).room_no, room)

    def test_unique_over_grid(self):
        """รหัสแขกต่างกัน -> เลขห้องต่างกัน และเป็นจำนวนเต็มบวกทั้งหมด"""
        rooms = {}
        for c in range(1, 61):
            for s in range(1, 61):
                room = Guest.calculate_room_no(c, s)
                self.assertGreaterEqual(room, 1)
                self.assertNotIn(room, rooms, f"{(c, s)} ซ้ำกับ {rooms.get(room)}")
                rooms[room] = (c, s)
        self.assertEqual(len(rooms), 60 * 60)

    def test_no_gaps_on_diagonals(self):
        """ทุกรหัสที่ c+s <= m+1 ได้เลขห้อง 1..m(m+1)/2 ครบทุกเลข ไม่ซ้ำไม่ขาด (ส่วนของเหตุผลว่าทำไมไม่ซ้ำ)"""
        m = 40
        rooms = [Guest.calculate_room_no(c, s)
                 for c in range(1, m + 1) for s in range(1, m + 1) if c + s <= m + 1]
        self.assertEqual(sorted(rooms), list(range(1, m * (m + 1) // 2 + 1)))

    def test_pure_integer_arithmetic(self):
        """คำนวณด้วยจำนวนเต็มล้วน ค่าใหญ่ไม่เพี้ยนแบบทศนิยม"""
        for c, s in [(10 ** 20, 10 ** 20), (10 ** 18 + 7, 3), (5, 10 ** 17)]:
            a, b = c - 1, s - 1
            expected = comb(a + b + 1, 2) + b + 1  # รูปสามเหลี่ยมคนละแบบกับสูตรในโค้ด
            room = Guest.calculate_room_no(c, s)
            self.assertIsInstance(room, int)
            self.assertEqual(room, expected)

    def test_room_depends_only_on_guest_code(self):
        """เลขห้องไม่ขึ้นกับลำดับที่เพิ่มแขก (ห้ามใช้ 'เลขล่าสุด + 1')"""
        codes = [(1, 1), (2, 1), (1, 2), (3, 3), (2, 5)]
        forward = HotelSystem(3, 8, 0, [])
        backward = HotelSystem(3, 8, 0, [])
        for c, s in codes:
            forward.add_guest(c, s)
        for c, s in reversed(codes):
            backward.add_guest(c, s)
        for c, s in codes:
            self.assertEqual(forward.search_by_id(c, s), backward.search_by_id(c, s))


class TestRoomLookupRoundTrip(unittest.TestCase):
    def test_search_by_node_room_inverts_formula(self):
        hotel = HotelSystem(4, 8, 3, [20, 15, 10], salt="1")
        for (c, s), guest in hotel.guests_by_id.items():
            self.assertEqual(hotel.search_by_node_room(guest.node_id, guest.room_no), (c, s))

    def test_address_pairs_are_unique(self):
        """(node_id, room_no) ไม่ซ้ำกันเลยทั้งโรงแรม"""
        hotel = HotelSystem(4, 8, 3, [20, 15, 10], salt="2")
        addresses = [(g.node_id, g.room_no) for g in hotel.guests_by_id.values()]
        self.assertEqual(len(addresses), len(set(addresses)))
        self.assertEqual(len(addresses), 45)


class TestGuestClass(unittest.TestCase):
    def test_valid_guest(self):
        g = Guest(2, 3)
        self.assertEqual((g.c, g.s), (2, 3))
        self.assertEqual(g.guest_id, (2, 3))
        self.assertEqual(g.hash_key, "guest:2:3")
        self.assertIsNone(g.node_id)

    def test_rejects_non_integer(self):
        for c, s in [(1.5, 1), (1, "2"), ("1", 1), (None, 1), (1, None)]:
            with self.subTest(c=c, s=s):
                with self.assertRaises(TypeError):
                    Guest(c, s)

    def test_rejects_non_positive(self):
        for c, s in [(0, 1), (1, 0), (-1, 5), (5, -3)]:
            with self.subTest(c=c, s=s):
                with self.assertRaises(ValueError):
                    Guest(c, s)

    def test_node_id_setter_validates_type(self):
        g = Guest(1, 1)
        g.node_id = "3"
        self.assertEqual(g.node_id, "3")
        g.node_id = None
        self.assertIsNone(g.node_id)
        with self.assertRaises(TypeError):
            g.node_id = 3

    def test_equality_and_hash(self):
        self.assertEqual(Guest(1, 2), Guest(1, 2))
        self.assertNotEqual(Guest(1, 2), Guest(2, 1))
        self.assertEqual(len({Guest(1, 2), Guest(1, 2), Guest(2, 1)}), 2)


if __name__ == "__main__":
    unittest.main()
