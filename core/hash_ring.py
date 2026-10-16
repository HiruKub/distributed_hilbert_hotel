import hashlib
import bisect


def hash64(text):       # 8 bytes = 64 bits
    hash_byte = hashlib.sha256(text.encode('utf-8')).digest()
    return int.from_bytes(hash_byte[:8], byteorder='big')


class HashRing:
    def __init__(self, v_node, salt=""):
        if not isinstance(v_node, int) or isinstance(v_node, bool) or v_node < 1:
            raise ValueError("v_node must be an integer >= 1")
        self._v_node = v_node
        self._salt = str(salt)
        self._ring = []
        self._nodes = set()

    @property
    def v_node(self):
        return self._v_node

    @property
    def salt(self):
        return self._salt

    @property
    def node_count(self):
        return len(self._nodes)

    @property
    def point_count(self):
        return len(self._ring)

    def __len__(self):
        return len(self._nodes)

    def __contains__(self, node_id):
        return node_id in self._nodes

    def __repr__(self):
        return f"HashRing(N={self.node_count}, V={self._v_node}, salt={self._salt!r})"

    def _node_position(self, node_id, j):
        return hash64(f"{self.salt}node:{node_id}:{j}")

    def _guest_position(self, c, s):
        return hash64(f"{self.salt}guest:{c}:{s}")

    # เอาไว้เผื่ออยากใช้
    def has_node(self, node_id):
        return node_id in self._nodes

    def get_all_nodes(self):
        return sorted(self._nodes)

    def get_points(self, node_id):      # ดึงตัวเลขตำแหน่ง hash
        points = []
        for item in self._ring:
            if item[1] == node_id:
                points.append(item[0])
        return points

    def add_node(self, node_id):
        # เพิ่มรหัสอาคารที่มีอยู่แล้ว
        if node_id in self._nodes:
            return False

        self._nodes.add(node_id)

        for j in range(self._v_node):
            position = self._node_position(node_id, j)
            # ถ้า position ตรง จะไปเทียบ node_id
            bisect.insort(self._ring, (position, node_id, j))
        return True

    def get_node(self, c, s):   # c = ที่มา , s = ลำดับ
        if not self._ring:
            return None

        guest_pos = self._guest_position(c, s)

        idx = bisect.bisect_left(self._ring, (guest_pos,))

        # ไม่มีจุดที่มีตำแหน่งมากกว่าหรือเท่ากับแขก ให้วนกลับไปเลือกจุดแรกของวงแหวน
        if idx >= len(self._ring):
            idx = 0

        return self._ring[idx][1]    # ดึง node_id ใน tuple

    def remove_node(self, node_id):
        # ลบรหัสอาคารที่ไม่มีอยู่
        if node_id not in self._nodes:
            return False

        # ลบอาคารสุดท้าย แม้ไม่มีแขก อาคาร >= 1
        if len(self._nodes) == 1:
            return False

        self._nodes.remove(node_id)

        new_ring = []
        for item in self._ring:      # check ทีละ tuple
            if item[1] != node_id:
                new_ring.append(item)

        self._ring = new_ring        # เขียนทับ
        return True
