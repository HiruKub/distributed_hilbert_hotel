from core.hash_ring import hash64
from core.avl_tree import OrderStatisticAVLTree


class HashModN:
    def __init__(self, salt=""):
        self._salt = str(salt)
        self._nodes = OrderStatisticAVLTree()

    @property
    def salt(self):
        return self._salt

    @property
    def node_count(self):
        return len(self._nodes)

    def __len__(self):
        return len(self._nodes)

    def __contains__(self, node_id):
        return node_id in self._nodes

    def __repr__(self):
        return f"HashModN(N={self.node_count}, salt={self._salt!r})"

    def _guest_position(self, c, s):
        return hash64(f"{self._salt}guest:{c}:{s}")

    def has_node(self, node_id):
        return node_id in self._nodes

    def get_all_nodes(self):
        return self._nodes.get_sorted_values()

    def add_node(self, node_id):
        if node_id in self._nodes:
            return False
        return self._nodes.append(node_id)

    def get_node(self, c, s):
        n = len(self._nodes)
        if n == 0:
            return None

        hashed = self._guest_position(c, s)
        idx = hashed % n
        return self._nodes.get_by_index(idx)

    def remove_node(self, node_id):
        if node_id not in self._nodes:
            return False
        if len(self._nodes) == 1:
            return False
        return self._nodes.remove(node_id)
