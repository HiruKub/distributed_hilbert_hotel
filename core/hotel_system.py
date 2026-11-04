from enum import Enum
class HashType(Enum):
    HASH_RING = "hash_ring"
    HASH_MOD_N = "hash_mod_n"

class MigrationRecord:
    def __init__(self, guest_id, old_node, new_node, room_no):
        self.__guest_id = guest_id
        self.__old_node = old_node
        self.__new_node = new_node
        self.__room_no = room_no

    @property
    def guest_id(self): return self.__guest_id
    @property
    def old_node(self): return self.__old_node
    @property
    def new_node(self): return self.__new_node
    @property
    def room_no(self): return self.__room_no

    def __repr__(self):
        return (f"MigrationRecord:\tguest:{self.__guest_id}\told_node:{self.__old_node}\tnew_node:{self.__new_node}\troom_no:{self.__room_no}")

class MigrationReport:
    def __init__(self, total_guests_k):
        self.__total_guests_k = total_guests_k
        self.__migrations = []

    @property
    def total_guests_k(self): return self.__total_guests_k
    @property
    def migrations(self): return self.__migrations
    @property
    def migrated_count(self): return len(self.__migrations)
    @property
    def migration_rate(self):
        if self.__total_guests_k == 0: return 0.0
        return self.migrated_count / self.__total_guests_k
    @property
    def rate_status(self):
        if self.__total_guests_k == 0: return "ไม่คำนวณอัตราเพราะไม่มีแขก"
        return f"{self.migration_rate:.4f} ({self.migrated_count}/{self.__total_guests_k})"

    def append_migration(self, record: MigrationRecord):
        self.__migrations.append(record)

    def generate_summary(self) -> str:
        """สร้างข้อความสรุปรายงานการย้าย (Migration Report)"""
        lines = [
            "==================================================",
            "             MIGRATION REPORT SUMMARY             ",
            "==================================================",
            f"จำนวนแขกทั้งหมดในระบบ (K) : {self.__total_guests_k}",
            f"จำนวนแขกที่ย้าย          : {self.migrated_count}",
            f"อัตราการย้าย (Rate)      : {self.rate_status}",
            "--------------------------------------------------",
            "รายการการย้ายแขก (Migration List):"
        ]
        
        if not self.migrations:
            lines.append("  (ไม่มีการย้ายแขกในรอบนี้)")
        else:
            for idx, m in enumerate(self.migrations, 1):
                c, s = m.guest_id
                lines.append(
                    f"  {idx:2d}. รหัสแขก ({c}, {s}) | "
                    f"อาคารเดิม: {m.old_node:>2s} -> อาคารใหม่: {m.new_node:>2s} | "
                    f"หมายเลขห้อง: {m.room_no}"
                )
        lines.append("==================================================")
        return "\n".join(lines)

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
                
        from core.hash_ring import HashRing
        from core.hash_mod_n import HashModN
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
        from core.guest import Guest
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

        report = MigrationReport(len(self.__guests_by_id))

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

                        record = MigrationRecord((c, s), target_node, node_id, self.__guests_by_id[(c, s)].room_no)
                        report.append_migration(record)

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
                    record = MigrationRecord((c, s), old_node, new_node, guest.room_no)
                    report.append_migration(record)

        return report
    
    def remove_node(self, node_id: str):
        if node_id not in self.__guests_by_node:
            raise ValueError("ไม่มีอาคารนี้ในระบบ")

        if len(self.__guests_by_node) <= 1:
            raise ValueError("ไม่สามารถลบอาคารได้ เนื่องจากต้องมีอาคารอย่างน้อย 1 อาคารในระบบเสมอ")

        report = MigrationReport(len(self.__guests_by_id))

        if self.__mode == HashType.HASH_RING:
            migrate = list(self.__guests_by_node[node_id])

            self.__router.remove_node(node_id)
            del self.__guests_by_node[node_id]

            for c, s in migrate:
                target_node = self.__router.get_node(c, s)
                self.__guests_by_node[target_node].add((c, s))
                self.__guests_by_id[(c, s)].node_id = target_node
                record = MigrationRecord((c, s), node_id, target_node, self.__guests_by_id[(c, s)].room_no)
                report.append_migration(record)

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
                    record = MigrationRecord((c, s), old_node, new_node, guest.room_no)
                    report.append_migration(record)

        return report