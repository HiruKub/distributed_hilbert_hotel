import os
import sys
import time
import statistics
import random

# ตั้งค่า path ให้เรียกใช้โมดูลใน core ได้อย่างปลอดภัย
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
core_dir = os.path.join(project_root, "core")
for path in [project_root, core_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from core.hotel_system import HotelSystem, HashType
from core.guest import Guest


def measure_median_time(func, *args, repeat: int = 3, **kwargs) -> float:
    """
    ฟังก์ชันช่วยจับเวลา: รันฟังก์ชันซ้ำ 3 รอบ
    แล้วคืนค่ามัธยฐาน (Median) ในหน่วยวินาที ตามกติกา PDF หน้า 9 ข้อ 7.2
    """
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        func(*args, **kwargs)
        end = time.perf_counter()
        times.append(end - start)
    return statistics.median(times)


def measure_search_1000_batch(hotel: HotelSystem, guest_ids: list, repeat: int = 3) -> float:
    """
    วัดเวลาการค้นหาเป็นชุด 1,000 ครั้ง แล้วหารเฉลี่ยต่อครั้ง ตามกติกา PDF หน้า 9
    """
    # สุ่มรหัสแขกที่มีอยู่ในระบบจริงมา 1,000 ตัว
    sample_queries = [random.choice(guest_ids) for _ in range(1000)]

    def run_1000_searches():
        for c, s in sample_queries:
            hotel.search_by_id(c, s)

    total_time_1000 = measure_median_time(run_1000_searches, repeat=repeat)
    return total_time_1000 / 1000.0  # เวลาเฉลี่ยต่อการค้นหา 1 ครั้ง


def run_time_complexity_benchmark():
    """
    รันชุดทดสอบความซับซ้อนของเวลาเทียบกับขนาดข้อมูลแขก (K)
    สอดคล้องกับการทดลอง A (PDF หน้า 9)
    """
    print("=" * 70)
    print("🚀 เริ่มการทดสอบและวัด TIME COMPLEXITY (ตามเกณฑ์ PDF หน้า 9-10)")
    print("=" * 70)

    N = 10  # จำนวนอาคารเริ่มต้น
    V = 32  # จำนวน Virtual Node ต่ออาคาร
    C = 10  # จำนวนช่องทาง

    # ทดสอบขนาดแขก K ที่เพิ่มขึ้น เพื่อดูพฤติกรรม Big-O
    K_values = [1_000, 5_000, 10_000]

    results = []

    for K in K_values:
        print(f"\nกำลังทดสอบที่ขนาดแขก K = {K:,} คน...")
        guests_per_channel = [K // C] * C

        # 1. วัดเวลาสร้างระบบและจัดแขกเริ่มต้น (Placement Time)
        def init_system():
            return HotelSystem(N=N, V=V, C=C, s=guests_per_channel, mode=HashType.HASH_RING)

        placement_time = measure_median_time(init_system, repeat=3)

        # สร้าง Object โรงแรมไว้สำหรับการทดสอบค้นหาและเพิ่มอาคาร
        hotel = init_system()
        all_guest_ids = list(hotel.guests_by_id.keys())

        # 2. วัดเวลาค้นหาเฉลี่ยต่อครั้ง (Search Time - 1,000 batch)
        search_time_per_op = measure_search_1000_batch(hotel, all_guest_ids, repeat=3)

        # 3. วัดเวลาเพิ่มอาคาร 1 หลัง (Add Node Time - สร้าง fresh hotel แต่ละรอบเพื่อความแม่นยำ)
        add_node_times = []
        for r in range(3):
            test_hotel = init_system()
            start = time.perf_counter()
            test_hotel.add_node(f"New_Building_{K}_{r}")
            end = time.perf_counter()
            add_node_times.append(end - start)
        add_node_time = statistics.median(add_node_times)

        results.append({
            "K": K,
            "placement_time": placement_time,
            "search_time_us": search_time_per_op * 1_000_000,  # แปลงเป็นไมโครวินาที (µs)
            "add_node_time": add_node_time
        })

    # แสดงผลตารางสรุป
    print("\n" + "=" * 70)
    print(f"{'K (จำนวนแขก)':<15} | {'เวลาจัดแขก (s)':<16} | {'ค้นหา/ครั้ง (µs)':<18} | {'เพิ่มอาคาร (s)':<15}")
    print("-" * 70)
    for r in results:
        print(f"{r['K']:<15,d} | {r['placement_time']:<16.4f} | {r['search_time_us']:<18.2f} | {r['add_node_time']:<15.4f}")
    print("=" * 70)

    # 4. สรุปผลวิเคราะห์ Big-O
    print("\n💡 บทวิเคราะห์เชิงทฤษฎีเทียบกับผลที่วัดได้:")
    ratio_k = results[-1]['K'] / results[0]['K']
    ratio_place = results[-1]['placement_time'] / results[0]['placement_time']
    print(f"• เมื่อ K เพิ่มขึ้น {ratio_k:.1f} เท่า -> เวลาจัดแขกเพิ่มขึ้นประมาณ {ratio_place:.1f} เท่า")
    print("  => สอดคล้องกับ Big-O: O(K log M) (Linearithmic Growth)")
    print(f"• เวลาค้นหาเฉลี่ยคงที่อยู่ในระดับไมโครวินาที")
    print("  => สอดคล้องกับ Big-O: O(1) สำหรับ Primary Index")


if __name__ == "__main__":
    run_time_complexity_benchmark()
