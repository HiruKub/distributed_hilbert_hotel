import hashlib


class Guest:
    def __init__(self, channel_id: int, sequence_id: int, node_id: str = None):
        if not isinstance(channel_id, int) or not isinstance(channel_id, int):
            raise TypeError("channel_id and sequence_id must be int")

        if channel_id < 1 or sequence_id < 1:
            raise ValueError("channel_id and sequence_id must >= 1")

        self._c = channel_id
        self._s = sequence_id
        self._node_id = node_id
        self._room_no = self.calculatate_room_no(self.c, self.s)

        pass

    @staticmethod
    def calculatate_room_no(c: int, s: int):
        a = c - 1
        b = s - 1
        return ((a + b) * (a + b + 1)) // 2 + b + 1

    @property
    def c(self):
        return self._c

    @property
    def s(self):
        return self._s

    @property
    def room_no(self):
        return self._room_no

    @property
    def node_id(self):
        return self._node_id

    @node_id.setter
    def node_id(self, new_node):
        if new_node is not None and not isinstance(new_node, str):
            raise TypeError("node_id must be string or None")
        self._node_id = new_node

    @property
    def guest_id(self):
        return (self.c, self.s)

    @property
    def hash_key(self):
        return f"guest:{self.c}:{self.s}"
    

    def __repr__(self):  # เผื่ออยาก debug ตอน guest อยู่ใน list หรือ tuple
        return f"Guest(c = {self.c} , s = {self.s})"

    def __eq__(self, other):
        if isinstance(other, Guest):
            return self.guest_id == other.guest_id
        return False

    def __hash__(self):
        return self._room_no
