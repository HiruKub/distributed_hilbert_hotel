import hashlib
import bisect


class HashRing:
    def __init__(self, v_node):
        self.v = v_node
        self.ring = []
        self.added_nodes = set()    # เวลา loop จะใช้ O(1)

    def _hash(self, text):
        hash_byte = hashlib.sha256(text.encode('utf-8')).digest()
        hashed = hash_byte[:8]      # 8 bytes = 64 bits
        return int.from_bytes(hashed, byteorder='big')

    def add_node(self, node_id):
        # เพิ่มรหัสอาคารที่มีอยู่แล้ว
        if node_id in self.added_nodes:
            return

        self.added_nodes.add(node_id)

        for j in range(self.v):
            text = f"node:{node_id}:{j}"
            position = self._hash(text)
            # ถ้า position ตรง จะไปเทียบ node_id
            bisect.insort(self.ring, (position, node_id, j))

    def get_node(self, c, s):   # c = ที่มา , s = ลำดับ
        if not self.ring:
            return None

        text = f"guest:{c}:{s}"
        guest_pos = self._hash(text)

        # 2 ตัวท้ายใส่เพื่อให้ครบตำแหน่ง
        idx = bisect.bisect_left(self.ring, (guest_pos, "", 0))

        # ากไม่มีจุดที่มีตำแหน่งมากกว่าหรือเท่ากับแขก ให้วนกลับไปเลือกจุดแรกของวงแหวน
        if idx >= len(self.ring):
            idx = 0

        return self.ring[idx][1]    # ดึง node_id ใน tuple

    def remove_node(self, node_id):
        # ลบรหัสอา่คารที่ไม่มีอยู่
        if node_id not in self.added_nodes:
            return

        # ลบอาคารสุดท้าย แม้ไม่มีแขก อาคาร >= 1
        if len(self.added_nodes) == 1 and node_id in self.added_nodes:
            return

        self.added_nodes.remove(node_id)

        new_ring = []
        for item in self.ring:      # check ทีละ tuple
            if item[1] != node_id:
                new_ring.append(item)

        self.ring = new_ring        # เขียนทับ
