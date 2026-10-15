from hash_ring import hash64

class HashModN:
    def __init__(self, salt=""):
        self.salt = salt
        self.nodes = []

    def add_node(self, node_id):
        if node_id in self.nodes:
            return False
        self.nodes.append(node_id)
        return True

    def get_node(self, c, s):
        if not self.nodes:
            return None

        text = f"{self.salt}guest:{c}:{s}"
        hashed = hash64(text)

        idx = hashed % len(self.nodes)

        return self.nodes[idx]

    def remove_node(self, node_id):
        if node_id not in self.nodes:
            return False
        if len(self.nodes) == 1:
            return False
        self.nodes.remove(node_id)
        return True