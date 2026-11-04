from enum import Enum
class HashType(Enum):
    HASH_RING = "hash_ring"
    HASH_MOD_N = "hash_mod_n"

class HotelSystem:
    def __init__(
        self, 
        N: int, 
        V: int, 
        C: int, 
        s: list[int], 
        mode: HashType = HashType.HASH_RING,
        salt: str = ""):
        self.__validate_init_params(N, C, s)
                
        from hash_ring import HashRing
        from hash_mod_n import HashModN
        self.__router = HashRing(V, str(salt)) if mode == HashType.HASH_RING else HashModN(str(salt))
        self.__guests_by_id = {}
        self.__guests_by_node = {}

        self.__init_nodes(N)
        self.__init_guests(s)

        self.__mode = mode

    def __validate_init_params(self, N: int, C: int, s: list[int]):
        if N < 1: 
            raise ValueError("เริ่มระบบด้วยจำนวนอาคารอย่างน้อย 1 (N >= 1)")
        if len(s) != C: 
            raise ValueError("จำนวนช่องทางไม่สัมพันธ์กับจำนวนแขกของแต่ละช่องทาง")
    def __init_nodes(self, N):
        for i in range(1, N+1):
            node_id = str(i)
            self.__router.add_node(node_id)
            self.__guests_by_node[node_id] = set()
    def __init_guests(self, s: list[int]):
        for channel_idx, count in enumerate(s):
            c = channel_idx + 1  # c เริ่มที่ 1
            if count < 0: raise ValueError(f"จำนวนแขกที่เข้าพักของช่องทางที่ {channel_idx} เป็นจำนวนติดลบ")
            for seq in range(1, count + 1):  # s (sequence) เริ่มที่ 1 เสมอ
                self.add_guest(c, seq)

    @property
    def guests_by_id(self): return self.__guests_by_id
    @property
    def guests_by_node(self): return self.__guests_by_node
    @property
    def router(self): return self.__router
    @property
    def mode(self): return self.__mode.value

    # Method
    def add_guest(self, c: int, s: int):
        node_id = self.__router.get_node(c, s)

        # duplicate 
        if (c, s) in self.__guests_by_id.keys(): raise ValueError(f"มีการเพิ่มแขก ({c},{s})ในระบบแล้ว")
        
        # บันทึกลง Primary Index
        from guest import Guest
        self.__guests_by_id[(c, s)] = Guest(c, s, node_id)

        # บันทึกลง Secondary Index
        if node_id not in self.__guests_by_node:
            self.__guests_by_node[node_id] = set()
        self.__guests_by_node[node_id].add((c, s))

        return True
    def add_guest_group(self, c: int, s_start: int, count: int):
        if not isinstance(c, int) or c < 1:
            raise ValueError("หมายเลขช่องทาง c ต้องเป็นจำนวนเต็ม >= 1")
        if not isinstance(s_start, int) or s_start < 1:
            raise ValueError("ลำดับเริ่มต้น s_start ต้องเป็นจำนวนเต็ม >= 1")
        if not isinstance(count, int) or count < 0:
            raise ValueError("จำนวนแขก count ต้องไม่ติดลบ")

        if count == 0: return True

        target_range = range(s_start, s_start + count)
        for s in target_range:
            if (c, s) in self.__guests_by_id: 
                raise ValueError("ในช่วงมีแขกที่รหัสทับกับแขกที่มีอยู่ ไม่สามารถเพิ่มแขกได้ทั้งกลุ่ม")
        for s in target_range: self.add_guest(c, s)

        return True
    def remove_guest(self, c: int, s: int):
        if not isinstance(c, int) or c < 1:
            raise ValueError("หมายเลขช่องทาง c ต้องเป็นจำนวนเต็ม >= 1")
        if not isinstance(s, int) or s < 1:
            raise ValueError("ลำดับ s ต้องเป็นจำนวนเต็ม >= 1")
        if (c, s) not in self.__guests_by_id:
            raise ValueError("ไม่มีแขกในระบบ")

        node_id = self.__router.get_node(c, s)

        del self.__guests_by_id[(c, s)]
        if node_id in self.__guests_by_node:
            self.__guests_by_node[node_id].remove((c, s))

        return True

    def search_by_id(self, c, s):
        if not isinstance(c, int) or c < 1:
            raise ValueError("หมายเลขช่องทาง c ต้องเป็นจำนวนเต็ม >= 1")
        if not isinstance(s, int) or s < 1:
            raise ValueError("ลำดับ s ต้องเป็นจำนวนเต็ม >= 1")

        result = self.__guests_by_id.get((c, s))
        if not result: raise ValueError("ไม่พบรหัสแขกที่ค้นหา")

        return result.node_id, result.room_no
    def search_by_node_room(self, node_id, room_no):
        if node_id not in self.__guests_by_node:
            raise ValueError(f"ไม่พบ Node ID '{node_id}' ในระบบ")

        import math
        z_prime = room_no - 1
        w = int((math.isqrt(8 * z_prime + 1) - 1) // 2)
        t = (w * (w + 1)) // 2
        b = z_prime - t
        a = w - b

        c = a + 1
        s = b + 1

        result = self.__guests_by_id.get((c, s))
        if result and result.node_id == node_id: 
            return result.c, result.s

        raise ValueError(f"ไม่พบแขกที่ค้นหา")

    def add_node(self, node_id: str):
        if node_id in self.__guests_by_node:
            raise ValueError("มีอาคารนี้อยู่ในระบบแล้ว")

        if self.__mode == HashType.HASH_RING:
            affected_nodes = set()
            for j in range(self.__router.v_node):
                position = self.__router._node_position(node_id, j)
                successor_node = self.__router.get_node_by_position(position)
                if successor_node and successor_node != node_id:
                    affected_nodes.add(successor_node)

            self.__router.add_node(node_id)
            self.__guests_by_node[node_id] = set()

            for target_node in affected_nodes:
                current_guests = list(self.__guests_by_node[target_node])
                for c, s in current_guests:
                    if self.__router.get_node(c, s) == node_id:
                        self.__guests_by_node[target_node].remove((c, s))
                        self.__guests_by_node[node_id].add((c, s))
                        self.__guests_by_id[(c, s)].node_id = node_id

        else:
            self.__router.add_node(node_id)
            self.__guests_by_node[node_id] = set()
            for (c, s), guest in list(self.__guests_by_id.items()):
                new_node = self.__router.get_node(c, s)
                old_node = guest.node_id
                if new_node != old_node:
                    self.__guests_by_node[old_node].remove((c, s))
                    self.__guests_by_node[new_node].add((c, s))
                    guest.node_id = new_node

        return True
    def remove_node(self, node_id: str):
        if node_id not in self.__guests_by_node:
            raise ValueError("ไม่มีอาคารนี้ในระบบ")

        if len(self.__guests_by_node) <= 1:
            raise ValueError("ไม่สามารถลบอาคารได้ เนื่องจากต้องมีอาคารอย่างน้อย 1 อาคารในระบบเสมอ")

        if self.__mode == HashType.HASH_RING:
            migrate = list(self.__guests_by_node[node_id])

            self.__router.remove_node(node_id)
            del self.__guests_by_node[node_id]

            for c, s in migrate:
                target_node = self.__router.get_node(c, s)
                self.__guests_by_node[target_node].add((c, s))
                self.__guests_by_id[(c, s)].node_id = target_node

        else:
            self.__router.remove_node(node_id)
            del self.__guests_by_node[node_id]

            for (c, s), guest in list(self.__guests_by_id.items()):
                new_node = self.__router.get_node(c, s)
                old_node = guest.node_id
                if new_node != old_node:
                    if old_node in self.__guests_by_node:
                        self.__guests_by_node[old_node].remove((c, s))
                    self.__guests_by_node[new_node].add((c, s))
                    guest.node_id = new_node

        return True

import unittest


class TestHotelSystemInitialization(unittest.TestCase):
    """1. ทดสอบการเริ่มต้นระบบและการตรวจสอบค่านำเข้า (Initialization & Validation)"""

    def test_init_success_both_modes(self):
        """ทดสอบการสร้างระบบสำเร็จทั้ง 2 โหมด"""
        for mode in [HashType.HASH_RING, HashType.HASH_MOD_N]:
            with self.subTest(mode=mode.value):
                hotel = HotelSystem(N=3, V=16, C=2, s=[5, 10], mode=mode)
                self.assertEqual(len(hotel.guests_by_node), 3)
                self.assertEqual(len(hotel.guests_by_id), 15)
                self.assertEqual(hotel.mode, mode.value)

    def test_init_invalid_N_raises_error(self):
        """ทดสอบกรณี N < 1 ต้องเกิด ValueError"""
        with self.assertRaises(ValueError):
            HotelSystem(N=0, V=16, C=2, s=[5, 5])

    def test_init_channel_mismatch_raises_error(self):
        """ทดสอบกรณี C ไม่สัมพันธ์กับ len(s) ต้องเกิด ValueError"""
        with self.assertRaises(ValueError):
            HotelSystem(N=3, V=16, C=3, s=[5, 5])  # C=3 แต่ s มี 2 สมาชิก

    def test_init_negative_guest_count_raises_error(self):
        """ทดสอบกรณีจำนวนแขกในช่องทางเป็นค่าติดลบ"""
        with self.assertRaises(ValueError):
            HotelSystem(N=3, V=16, C=2, s=[5, -1])


class TestHotelSystemGuestOperations(unittest.TestCase):
    """2. ทดสอบการจัดการแขก (Add, Remove, Search Guest)"""

    def setUp(self):
        self.hotel = HotelSystem(N=3, V=16, C=2, s=[5, 5], mode=HashType.HASH_RING)

    def test_add_guest_duplicate_raises_error(self):
        """ทดสอบการเพิ่มแขกรหัสซ้ำ"""
        with self.assertRaises(ValueError):
            self.hotel.add_guest(1, 1)  # แขก (1,1) มีอยู่ในระบบตั้งแต่ init แล้ว

    def test_add_guest_group_success(self):
        """ทดสอบการเพิ่มแขกเป็นกลุ่มสำเร็จ"""
        initial_count = len(self.hotel.guests_by_id)
        self.assertTrue(self.hotel.add_guest_group(c=1, s_start=6, count=5))
        self.assertEqual(len(self.hotel.guests_by_id), initial_count + 5)

    def test_add_guest_group_duplicate_raises_error(self):
        """ทดสอบการเพิ่มแขกกลุ่มที่มีรหัสทับซ้อนกับแขกเดิม"""
        with self.assertRaises(ValueError):
            self.hotel.add_guest_group(c=1, s_start=4, count=5)  # ทับซ้อนที่ s=4, 5

    def test_remove_guest_success(self):
        """ทดสอบการลบแขกออกจากระบบสำเร็จ"""
        c, s = 1, 1
        node_id, _ = self.hotel.search_by_id(c, s)
        
        self.assertTrue(self.hotel.remove_guest(c, s))
        self.assertNotIn((c, s), self.hotel.guests_by_id)
        self.assertNotIn((c, s), self.hotel.guests_by_node[node_id])

    def test_remove_non_existent_guest_raises_error(self):
        """ทดสอบการลบแขกที่ไม่มีในระบบ"""
        with self.assertRaises(ValueError):
            self.hotel.remove_guest(99, 99)

    def test_search_by_id_success_and_fail(self):
        """ทดสอบการค้นหาแขกด้วย (c, s)"""
        node_id, room_no = self.hotel.search_by_id(1, 1)
        self.assertIsNotNone(node_id)
        self.assertGreater(room_no, 0)

        with self.assertRaises(ValueError):
            self.hotel.search_by_id(99, 99)

    def test_search_by_node_room(self):
        """ทดสอบการค้นหาแขกกลับด้วย (node_id, room_no)"""
        c_orig, s_orig = 1, 2
        node_id, room_no = self.hotel.search_by_id(c_orig, s_orig)
        
        c_found, s_found = self.hotel.search_by_node_room(node_id, room_no)
        self.assertEqual((c_orig, s_orig), (c_found, s_found))


class TestHotelSystemNodeOperations(unittest.TestCase):
    """3. ทดสอบการเพิ่ม/ลบ อาคาร และการย้ายแขก (Node Migration) ทั้ง 2 โหมด"""

    def test_add_and_remove_node_flow(self):
        """ทดสอบ Workflow การเพิ่มและลบอาคาร พร้อมตรวจสอบ Data Integrity ของทั้ง 2 โหมด"""
        for mode in [HashType.HASH_RING, HashType.HASH_MOD_N]:
            with self.subTest(mode=mode.value):
                hotel = HotelSystem(N=3, V=16, C=2, s=[10, 10], mode=mode)
                total_guests_initial = len(hotel.guests_by_id)

                # --- 1. ทดสอบ Add Node ---
                new_node = "4"
                self.assertTrue(hotel.add_node(new_node))
                self.assertIn(new_node, hotel.guests_by_node)

                # ตรวจสอบว่าไม่มีแขกสูญหายหลัง Re-hash
                self.assertEqual(len(hotel.guests_by_id), total_guests_initial)
                sum_guests_in_nodes = sum(len(g) for g in hotel.guests_by_node.values())
                self.assertEqual(total_guests_initial, sum_guests_in_nodes)

                # ตรวจสอบ Cross-Index Consistency หลัง Add Node
                for (c, s), guest in hotel.guests_by_id.items():
                    self.assertIn((c, s), hotel.guests_by_node[guest.node_id])

                # --- 2. ทดสอบ Remove Node ---
                self.assertTrue(hotel.remove_node(new_node))
                self.assertNotIn(new_node, hotel.guests_by_node)

                # ตรวจสอบความสมบูรณ์ของข้อมูลหลังลบอาคาร
                self.assertEqual(len(hotel.guests_by_id), total_guests_initial)
                sum_guests_after_remove = sum(len(g) for g in hotel.guests_by_node.values())
                self.assertEqual(total_guests_initial, sum_guests_after_remove)

                # ตรวจสอบ Cross-Index Consistency หลัง Remove Node
                for (c, s), guest in hotel.guests_by_id.items():
                    self.assertIn((c, s), hotel.guests_by_node[guest.node_id])

    def test_add_duplicate_node_raises_error(self):
        """ทดสอบการเพิ่มอาคารที่มีรหัสซ้ำ"""
        hotel = HotelSystem(N=3, V=16, C=2, s=[5, 5])
        with self.assertRaises(ValueError):
            hotel.add_node("1")

    def test_remove_non_existent_node_raises_error(self):
        """ทดสอบการลบอาคารที่ไม่เคยมีในระบบ"""
        hotel = HotelSystem(N=3, V=16, C=2, s=[5, 5])
        with self.assertRaises(ValueError):
            hotel.remove_node("999")

    def test_remove_last_node_protection(self):
        """ทดสอบระบบยับยั้งการลบอาคารจนหมด (ต้องเหลืออย่างน้อย 1 อาคารเสมอ)"""
        hotel = HotelSystem(N=2, V=16, C=1, s=[5])
        hotel.remove_node("2")  # เหลือ 1 อาคาร ("1")

        with self.assertRaises(ValueError):
            hotel.remove_node("1")


if __name__ == "__main__":
    unittest.main()