from hash_ring import hash64

class HashModN:
    def __init__(self, salt=""):
        self._salt = str(salt)
        self._nodes = []

    @property
    def salt(self):
        return self._salt

    @property
    def node_count(self):
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
        return sorted(self._nodes)

    def add_node(self, node_id):
        if node_id in self._nodes:
            return False
        self._nodes.append(node_id)
        return True

    def get_node(self, c, s):
        if not self._nodes:
            return None

        hashed = self._guest_position(c, s)
        idx = hashed % len(self._nodes)
        return self._nodes[idx]

    def remove_node(self, node_id):
        if node_id not in self._nodes:
            return False
        if len(self._nodes) == 1:
            return False
        self._nodes.remove(node_id)
        return True