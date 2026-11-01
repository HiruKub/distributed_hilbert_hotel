from hash_ring import HashRing, hash64
from hash_mod_n import HashModN
# สมมุติว่าเก็บ AVLTree และ HotelSystem ไว้ใน hotel_system.py
from hotel_system import HotelSystem
from tree import AVLTree


def run_add_building_tests():
    print("==========================================")
    print("      STARTING ADD_BUILDING TEST SUITE    ")
    print("==========================================")

    # ----------------------------------------------------
    # TEST 1: เพิ่มอาคารแรกสุดเข้าสู่ระบบ (node_count == 1)
    # ----------------------------------------------------
    router_ring = HashRing(3, "test_salt")
    hotel = HotelSystem(5, 100, router_ring)

    # Check-in แขกตัวอย่าง 5 คนเข้าสู่ระบบก่อนมีอาคาร
    test_guests = [(1, 1), (1, 2), (2, 1), (3, 5), (10, 20)]
    for idx, (c, s) in enumerate(test_guests):
        hotel.add_guest(c, s, room_index=idx + 1)

    relocated_b1 = hotel.add_building("B1")

    print("\n--- TEST 1: First Building Addition (B1) ---")
    print(f"จำนวนแขกที่ถูกย้ายไป B1: {len(relocated_b1)} คน (คาดหวัง: 5 คน)")
    assert len(relocated_b1) == 5, "FAILED: แขกทั้งหมดต้องถูกย้ายไปอาคารแรก"
    print("PASSED: แขกทั้งหมดถูกย้ายเข้าอาคารแรกสำเร็จ")

    # ----------------------------------------------------
    # TEST 2: เพิ่มอาคารที่สอง (Dynamic Scaling บน Hash Ring)
    # ----------------------------------------------------
    relocated_b2 = hotel.add_building("B2")

    print("\n--- TEST 2: Dynamic Scaling Addition (B2) ---")
    print(f"จำนวนแขกที่ย้ายจาก B1 ไป B2: {len(relocated_b2)} คน")

    # ตรวจสอบว่าเฉพาะแขกที่ถูกย้ายไป B2 เท่านั้นที่ตรงกับช่วง Virtual Nodes
    for guest, node_id in relocated_b2:
        expected_node = hotel.method.get_node(guest[0], guest[1])
        assert node_id == expected_node == "B2", f"FAILED: แขก {guest} ควรไปอยู่ B2"
    
    print(f"รายละเอียดแขกที่ย้ายไป B2: {relocated_b2}")
    print("PASSED: การย้ายแขกด้วย AVL Range Query สำเร็จถูกต้อง")

    # ----------------------------------------------------
    # TEST 3: เพิ่มอาคารซ้ำ (Duplicate Node ID)
    # ----------------------------------------------------
    relocated_b2_dup = hotel.add_building("B2")

    print("\n--- TEST 3: Duplicate Building ID (B2) ---")
    print(f"ผลลัพธ์การเพิ่ม B2 ซ้ำ: {relocated_b2_dup} (คาดหวัง: [])")
    assert relocated_b2_dup == [], "FAILED: การเพิ่มอาคารซ้ำต้องไม่เกิดการย้ายแขก"
    print("PASSED: ระบบป้องกันการเพิ่มอาคารซ้ำถูกต้อง")

    # ----------------------------------------------------
    # TEST 4: ทดสอบร่วมกับ HashModN Router (Modulo Hashing)
    # ----------------------------------------------------
    router_mod = HashModN(salt="test_salt")
    hotel_mod = HotelSystem(5, 100, router_mod)

    for idx, (c, s) in enumerate(test_guests):
        hotel_mod.add_guest(c, s, room_index=idx + 1)

    mod_b1 = hotel_mod.add_building("B1")
    mod_b2 = hotel_mod.add_building("B2")

    print("\n--- TEST 4: Modulo Hashing Router Fallback ---")
    print(f"HashModN - ย้ายเข้า B1: {len(mod_b1)} คน | ย้ายไป B2: {len(mod_b2)} คน")
    assert len(mod_b1) == 5, "FAILED: HashModN อาคารแรกต้องรับแขกทั้งหมด"
    print("PASSED: รองรับการใช้งาน HashModN สำเร็จ")

    print("\n==========================================")
    print("     ALL ADD_BUILDING TESTS PASSED!       ")
    print("==========================================")


if __name__ == "__main__":
    run_add_building_tests()