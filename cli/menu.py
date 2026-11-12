import os

from experiments.tree_version.hotel_system import HashType, HotelSystem
from experiments.run_experiments import (METHOD_NAME, MOD_N, RING, benchmark_once, run_b_case)
from utils.exporter import export_guests, export_migrations
from utils.reports import list_rooms, load_stats, verify_consistency

OUTPUT_DIR = "output"
DEFAULT_SHOW = 20


class CancelInput(Exception):
    """ผู้ใช้พิมพ์ q เพื่อยกเลิกคำสั่งปัจจุบัน"""


# ------------------------------------------------------------ รับค่า

def ask(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    text = input(f"{prompt}{suffix}: ").strip()
    if text.lower() == "q":
        raise CancelInput
    if text == "" and default is not None:
        return str(default)
    return text


def ask_int(prompt, minimum=None, default=None):
    while True:
        raw = ask(prompt, default)
        try:
            value = int(raw)
        except ValueError:
            print("  ! ต้องเป็นจำนวนเต็ม (พิมพ์ q เพื่อยกเลิก)")
            continue
        if minimum is not None and value < minimum:
            print(f"  ! ต้องมีค่า >= {minimum}")
            continue
        return value


def ask_node_id(prompt):
    while True:
        text = ask(prompt)
        if text:
            return text
        print("  ! รหัสอาคารต้องไม่ว่าง")


def ask_int_list(prompt, expected_count):
    while True:
        raw = ask(prompt).replace(",", " ").split()
        try:
            values = [int(x) for x in raw]
        except ValueError:
            print("  ! ต้องเป็นจำนวนเต็มคั่นด้วยเว้นวรรคหรือ ,")
            continue
        if len(values) != expected_count:
            print(f"  ! ต้องกรอก {expected_count} ค่า (กรอกมา {len(values)})")
            continue
        if any(v < 0 for v in values):
            print("  ! จำนวนแขกต้องไม่ติดลบ")
            continue
        return values


# ------------------------------------------------------------ เมนู

class HotelMenu:
    def __init__(self):
        self.hotel = None
        self.last_report = None
        self.actions = {
            "1": ("เริ่มระบบใหม่", self.init_system),
            "2": ("เพิ่มแขก (รายคน / เป็นกลุ่ม)", self.add_guests),
            "3": ("นำแขกออก", self.remove_guest),
            "4": ("เพิ่ม / ลบอาคาร (พร้อมรายงานการย้าย)", self.change_buildings),
            "5": ("ค้นหา (ด้วยรหัสแขก / ด้วยอาคาร+ห้อง)", self.search),
            "6": ("แสดงรายการห้องที่มีผู้พัก", self.show_rooms),
            "7": ("รายงานความสมดุลของโหลด", self.show_load),
            "8": ("วัดเวลาและหน่วยความจำ", self.benchmark),
            "9": ("เปรียบเทียบ Consistent Hashing กับ hash mod N", self.compare),
            "10": ("ส่งออกไฟล์ CSV", self.export),
        }

    # -- วนเมนูหลัก
    def run(self):
        print("=" * 56)
        print("   โรงแรมอนันต์แบบกระจาย (Distributed Hilbert's Hotel)")
        print("=" * 56)
        while True:
            self._print_menu()
            try:
                choice = input("เลือกเมนู: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nออกจากโปรแกรม")
                return
            if choice == "0":
                print("ออกจากโปรแกรม")
                return
            if choice not in self.actions:
                print("  ! ไม่มีเมนูนี้ เลือก 0-10")
                continue
            try:
                self.actions[choice][1]()
            except CancelInput:
                print("  ยกเลิกคำสั่งแล้ว")
            except (EOFError, KeyboardInterrupt):
                print("\nออกจากโปรแกรม")
                return
            except (ValueError, TypeError, KeyError, OSError) as err:
                print(f"  ! ทำรายการไม่สำเร็จ: {err}")
            except Exception as err:  # กันโปรแกรมหยุดทำงานด้วยเหตุไม่คาดคิด
                print(f"  ! เกิดข้อผิดพลาดที่ไม่คาดคิด ({type(err).__name__}): {err}")

    def _print_menu(self):
        print()
        print(self._status_line())
        print("-" * 56)
        for key, (label, _) in self.actions.items():
            print(f"  {key:>2}. {label}")
        print("   0. ออก")

    def _status_line(self):
        if self.hotel is None:
            return "สถานะ: ยังไม่ได้เริ่มระบบ (เลือกเมนู 1)"
        return (f"สถานะ: โหมด {self.hotel.mode} | อาคาร {len(self.hotel.guests_by_node)} หลัง"
                f" | แขก {len(self.hotel.guests_by_id):,} คน")

    def _need_hotel(self):
        if self.hotel is None:
            raise ValueError("ยังไม่ได้เริ่มระบบ กรุณาเลือกเมนู 1 ก่อน")
        return self.hotel

    # -- 1
    def init_system(self):
        N = ask_int("จำนวนอาคารเริ่มต้น N", minimum=1)
        V = ask_int("จำนวน virtual node ต่ออาคาร V", minimum=1, default=32)
        C = ask_int("จำนวนช่องทาง C", minimum=0)
        counts = ask_int_list(f"จำนวนแขกของแต่ละช่องทาง ({C} ค่า)", C) if C else []
        mode_text = ask("วิธีเลือกอาคาร (1 = Consistent Hashing, 2 = hash mod N)", default=1)
        mode = HashType.HASH_MOD_N if mode_text == "2" else HashType.HASH_RING
        salt = ask("salt", default="0")

        self.hotel = HotelSystem(N, V, C, counts, mode=mode, salt=salt)
        self.last_report = None
        print(f"  เริ่มระบบแล้ว: N={N}, V={V}, ช่องทาง={C}, แขก={sum(counts):,} คน, "
              f"โหมด={mode.value}, salt={salt!r}")

    # -- 2
    def add_guests(self):
        hotel = self._need_hotel()
        kind = ask("เพิ่มแบบ 1 = รายคน, 2 = เป็นกลุ่ม", default=1)
        c = ask_int("ช่องทาง c", minimum=1)
        if kind == "2":
            s_start = ask_int("ลำดับเริ่มต้น s_start", minimum=1)
            count = ask_int("จำนวนแขก", minimum=0)
            hotel.add_guest_group(c, s_start, count)
            print(f"  เพิ่มแขกช่องทาง {c} ลำดับ {s_start}..{s_start + count - 1} "
                  f"จำนวน {count:,} คนแล้ว" if count else "  จำนวน 0 คน ไม่มีการเปลี่ยนแปลง")
        else:
            s = ask_int("ลำดับ s", minimum=1)
            hotel.add_guest(c, s)
            node_id, room_no = hotel.search_by_id(c, s)
            print(f"  เพิ่มแขก ({c}, {s}) แล้ว -> อาคาร {node_id} ห้อง {room_no}")

    # -- 3
    def remove_guest(self):
        hotel = self._need_hotel()
        c = ask_int("ช่องทาง c", minimum=1)
        s = ask_int("ลำดับ s", minimum=1)
        hotel.remove_guest(c, s)
        print(f"  นำแขก ({c}, {s}) ออกแล้ว")

    # -- 4
    def change_buildings(self):
        hotel = self._need_hotel()
        action = ask("1 = เพิ่มอาคาร, 2 = ลบอาคาร", default=1)
        node_id = ask_node_id("รหัสอาคาร")
        if action == "2":
            report = hotel.remove_node(node_id)
            print(f"  ลบอาคาร {node_id} แล้ว")
        else:
            report = hotel.add_node(node_id)
            print(f"  เพิ่มอาคาร {node_id} แล้ว")
        self.last_report = report
        limit = ask_int("แสดงรายการย้ายกี่รายการ", minimum=0, default=DEFAULT_SHOW)
        self._print_report(report, limit)

    @staticmethod
    def _print_report(report, limit):
        print("-" * 56)
        print(f"  แขกทั้งหมด (K)  : {report.total_guests_k:,}")
        print(f"  จำนวนแขกที่ย้าย : {report.migrated_count:,}")
        print(f"  อัตราการย้าย    : {report.rate_status}")
        migrations = report.migrations
        if not migrations:
            print("  (ไม่มีการย้ายแขก)")
        else:
            shown = migrations[:limit]
            for i, m in enumerate(shown, 1):
                c, s = m.guest_id
                print(f"  {i:>4}. แขก ({c}, {s})  อาคาร {m.old_node} -> {m.new_node}"
                      f"  ห้อง {m.room_no}")
            print(f"  แสดง {len(shown):,} จาก {len(migrations):,} รายการ"
                  " (ส่งออกครบทุกรายการได้ที่เมนู 10)")
        print("-" * 56)

    # -- 5
    def search(self):
        hotel = self._need_hotel()
        kind = ask("ค้นด้วย 1 = รหัสแขก (c, s), 2 = (node_id, room_no)", default=1)
        if kind == "2":
            node_id = ask_node_id("รหัสอาคาร")
            room_no = ask_int("หมายเลขห้อง", minimum=1)
            c, s = hotel.search_by_node_room(node_id, room_no)
            print(f"  พบ: อาคาร {node_id} ห้อง {room_no} -> แขก ({c}, {s})")
        else:
            c = ask_int("ช่องทาง c", minimum=1)
            s = ask_int("ลำดับ s", minimum=1)
            node_id, room_no = hotel.search_by_id(c, s)
            print(f"  พบ: แขก ({c}, {s}) -> อาคาร {node_id} ห้อง {room_no}")

    # -- 6
    def show_rooms(self):
        hotel = self._need_hotel()
        rows = list_rooms(hotel)
        total = len(rows)
        if total == 0:
            print("  ยังไม่มีแขกพักอยู่")
            return
        limit = ask_int("แสดงกี่รายการ", minimum=0, default=DEFAULT_SHOW)
        print(f"  {'อาคาร':<8}{'ห้อง':>12}   แขก (c, s)")
        for r in rows[:limit]:
            print(f"  {r.node_id:<8}{r.room_no:>12}   ({r.c}, {r.s})")
        print(f"  แสดง {min(limit, total):,} จาก {total:,} รายการ "
              "(เรียงตามอาคารแล้วห้อง; ส่งออกครบได้ที่เมนู 10)")

    # -- 7
    def show_load(self):
        hotel = self._need_hotel()
        stats = load_stats(hotel)
        print(f"  จำนวนแขกต่ออาคาร (รวมอาคารที่มี 0 คน) ทั้งหมด {stats.node_count} อาคาร:")
        for node_id, count in stats.counts:
            print(f"    อาคาร {node_id:<6}: {count:,} คน")
        print(f"  แขกรวม   : {stats.total:,}")
        print(f"  สูงสุด   : {stats.maximum:,}")
        print(f"  ต่ำสุด   : {stats.minimum:,}")
        print(f"  เฉลี่ย   : {stats.mean:,.2f}")
        print(f"  ส่วนเบี่ยงเบนมาตรฐาน (ประชากร): {stats.std:,.2f}")
        if stats.cv is None:
            print("  CV       : ไม่คำนวณ เพราะไม่มีแขก")
        else:
            print(f"  CV (std/mean): {stats.cv:.4f}  (ยิ่งต่ำยิ่งสมดุล)")
        problems = verify_consistency(hotel)
        print("  ตรวจดัชนี: " + ("สอดคล้องกันทั้งหมด" if not problems
                                  else f"พบความไม่สอดคล้อง {len(problems)} จุด"))

    # -- 8
    def benchmark(self):
        print("  วัด 1 รอบ (รอบจับเวลาและรอบวัดหน่วยความจำแยกกัน) ใช้ระบบใหม่ ไม่กระทบข้อมูลปัจจุบัน")
        N = ask_int("N", minimum=1, default=10)
        V = ask_int("V", minimum=1, default=32)
        K = ask_int("K (จำนวนแขก 10 ช่องทาง)", minimum=1, default=10_000)
        salt = ask("salt", default="0")
        row = benchmark_once(N, V, K, RING, salt)
        print(f"  พารามิเตอร์: N={N}, V={V}, K={K:,}, salt={salt}, ช่องทาง=10, วิธี=ring")
        print(f"  สร้างวงแหวน       : {row['t_build_ring_s']:.6f} วินาที")
        print(f"  จัดแขก            : {row['t_place_guests_s']:.6f} วินาที")
        print(f"  เรียงรายการห้อง    : {row['t_sort_s']:.6f} วินาที")
        print(f"  ค้นด้วยรหัสแขก     : {row['t_search_by_id_us']:.3f} µs/ครั้ง "
              f"(ชุด {row['search_batch']:,} ครั้ง)")
        print(f"  ค้นด้วยอาคาร+ห้อง  : {row['t_search_by_room_us']:.3f} µs/ครั้ง")
        print(f"  คำนวณอาคารจากวงแหวน: {row['t_route_only_us']:.3f} µs/ครั้ง")
        print(f"  หน่วยความจำ (tracemalloc, เฉพาะที่ Python ติดตาม): "
              f"current {row['mem_current_mib']:.3f} MiB, peak {row['mem_peak_mib']:.3f} MiB")

    # -- 9
    def compare(self):
        print("  เปรียบเทียบด้วยแขกชุดเดียวกัน salt เดียวกัน และการเปลี่ยนอาคารแบบเดียวกัน")
        N = ask_int("N", minimum=2, default=10)
        V = ask_int("V", minimum=1, default=32)
        K = ask_int("K", minimum=1, default=10_000)
        salt = ask("salt", default="0")
        print(f"  พารามิเตอร์: N={N}, V={V}, K={K:,}, salt={salt}, ช่องทาง=10")
        print(f"  เพิ่มอาคารรหัส {N + 1} / ลบอาคารรหัส {(N + 1) // 2}")
        print(f"  {'วิธี':<8}{'คำสั่ง':<8}{'ย้าย':>8}{'อัตรา':>9}{'ค่าคาดหวัง':>12}{'เวลา(ms)':>11}"
              f"  ย้ายเฉพาะที่ควร")
        for mode in (RING, MOD_N):
            for r in run_b_case(N, V, K, mode, salt):
                print(f"  {r['method']:<8}{r['operation']:<8}{r['migrated_count']:>8,}"
                      f"{r['migration_rate']:>9.4f}{r['expected_rate']:>12.4f}"
                      f"{r['time_s'] * 1000:>11.3f}  "
                      f"{'ใช่' if r['only_expected_nodes_move'] else 'ไม่'}")

    # -- 10
    def export(self):
        hotel = self._need_hotel()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = ask("ไฟล์รายชื่อแขก", default=os.path.join(OUTPUT_DIR, "guests.csv"))
        rows = export_guests(hotel, path)
        print(f"  ส่งออกแขก {rows:,} แถว -> {path} (จำนวนแขกในระบบ {len(hotel.guests_by_id):,})")
        if self.last_report is None:
            print("  ยังไม่มีรายการย้ายให้ส่งออก (ทำเมนู 4 ก่อน)")
            return
        mpath = ask("ไฟล์รายการย้ายล่าสุด", default=os.path.join(OUTPUT_DIR, "migrations.csv"))
        moved = export_migrations(self.last_report, mpath)
        print(f"  ส่งออกรายการย้าย {moved:,} แถว -> {mpath}")


def main():
    HotelMenu().run()
