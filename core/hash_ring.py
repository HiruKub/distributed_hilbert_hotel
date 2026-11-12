import hashlib


def hash64(text):  # 8 bytes = 64 bits
    hash_byte = hashlib.sha256(text.encode('utf-8')).digest()
    return int.from_bytes(hash_byte[:8], byteorder='big')


class _StringAVLNode:
    def __init__(self, value):
        self.value = value
        self.left = None
        self.right = None
        self.height = 1


class _StringAVLSet:
    def __init__(self):
        self._root = None
        self._size = 0

    def __len__(self):
        return self._size

    def __contains__(self, value):
        curr = self._root
        while curr:
            if value == curr.value:
                return True
            curr = curr.left if value < curr.value else curr.right
        return False

    def _height(self, node):
        return node.height if node else 0

    def _balance_factor(self, node):
        return self._height(node.left) - self._height(node.right) if node else 0

    def _update_height(self, node):
        node.height = 1 + max(self._height(node.left),
                              self._height(node.right))

    def _rotate_right(self, y):
        x = y.left
        t2 = x.right
        x.right = y
        y.left = t2
        self._update_height(y)
        self._update_height(x)
        return x

    def _rotate_left(self, x):
        y = x.right
        t2 = y.left
        y.left = x
        x.right = t2
        self._update_height(x)
        self._update_height(y)
        return y

    def _rebalance(self, node):
        self._update_height(node)
        balance = self._balance_factor(node)
        if balance > 1:
            if self._balance_factor(node.left) < 0:
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        if balance < -1:
            if self._balance_factor(node.right) > 0:
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        return node

    def add(self, value):
        if value in self:
            return
        self._root = self._insert(self._root, value)
        self._size += 1

    def _insert(self, node, value):
        if not node:
            return _StringAVLNode(value)
        if value < node.value:
            node.left = self._insert(node.left, value)
        else:
            node.right = self._insert(node.right, value)
        return self._rebalance(node)

    def remove(self, value):
        if value not in self:
            raise KeyError(value)
        self._root = self._delete(self._root, value)
        self._size -= 1

    def _min_node(self, node):
        while node.left:
            node = node.left
        return node

    def _delete(self, node, value):
        if not node:
            return None
        if value < node.value:
            node.left = self._delete(node.left, value)
        elif value > node.value:
            node.right = self._delete(node.right, value)
        else:
            if not node.left:
                return node.right
            if not node.right:
                return node.left
            temp = self._min_node(node.right)
            node.value = temp.value
            node.right = self._delete(node.right, temp.value)
        return self._rebalance(node)

    def to_sorted_list(self):
        result = []

        def _inorder(node):
            if node:
                _inorder(node.left)
                result.append(node.value)
                _inorder(node.right)
        _inorder(self._root)
        return result


class _RingAVLNode:
    def __init__(self, position, node_id, j):
        self.position = position
        self.node_id = node_id
        self.j = j
        self.key = (position, node_id, j)
        self.left = None
        self.right = None
        self.height = 1


class HashRing:
    def __init__(self, v_node, salt=""):
        if not isinstance(v_node, int) or isinstance(v_node, bool) or v_node < 1:
            raise ValueError("v_node must be an integer >= 1")
        self._v_node = v_node
        self._salt = str(salt)
        self._root = None
        self._point_count = 0
        self._nodes = _StringAVLSet()

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
        return self._point_count

    def __len__(self):
        return len(self._nodes)

    def __contains__(self, node_id):
        return node_id in self._nodes

    def __repr__(self):
        return f"HashRing(N={self.node_count}, V={self._v_node}, salt={self._salt!r}, structure='AVLTree')"

    def _node_position(self, node_id, j):
        return hash64(f"{self.salt}node:{node_id}:{j}")

    def _guest_position(self, c, s):
        return hash64(f"{self.salt}guest:{c}:{s}")

    # ---------- AVL Tree Helpers ----------
    def _height(self, node):
        return node.height if node else 0

    def _balance_factor(self, node):
        return self._height(node.left) - self._height(node.right) if node else 0

    def _update_height(self, node):
        node.height = 1 + max(self._height(node.left),
                              self._height(node.right))

    def _rotate_right(self, y):
        x = y.left
        t2 = x.right
        x.right = y
        y.left = t2
        self._update_height(y)
        self._update_height(x)
        return x

    def _rotate_left(self, x):
        y = x.right
        t2 = y.left
        y.left = x
        x.right = t2
        self._update_height(x)
        self._update_height(y)
        return y

    def _rebalance(self, node):
        self._update_height(node)
        balance = self._balance_factor(node)
        if balance > 1:
            if self._balance_factor(node.left) < 0:
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)
        if balance < -1:
            if self._balance_factor(node.right) > 0:
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)
        return node

    def _insert_ring_node(self, node, position, node_id, j):
        if not node:
            return _RingAVLNode(position, node_id, j)
        new_key = (position, node_id, j)
        if new_key < node.key:
            node.left = self._insert_ring_node(node.left, position, node_id, j)
        else:
            node.right = self._insert_ring_node(
                node.right, position, node_id, j)
        return self._rebalance(node)

    def _min_ring_node(self, node):
        while node.left:
            node = node.left
        return node

    def _delete_ring_node(self, node, target_key):
        if not node:
            return None
        if target_key < node.key:
            node.left = self._delete_ring_node(node.left, target_key)
        elif target_key > node.key:
            node.right = self._delete_ring_node(node.right, target_key)
        else:
            if not node.left:
                return node.right
            if not node.right:
                return node.left
            temp = self._min_ring_node(node.right)
            node.position = temp.position
            node.node_id = temp.node_id
            node.j = temp.j
            node.key = temp.key
            node.right = self._delete_ring_node(node.right, temp.key)
        return self._rebalance(node)

    def _find_successor_node_id(self, pos: int):
        if not self._root:
            return None
        curr = self._root
        successor = None
        while curr:
            if curr.position >= pos:
                successor = curr
                curr = curr.left
            else:
                curr = curr.right

        if successor is None:
            successor = self._min_ring_node(self._root)

        return successor.node_id

    # ---------- Public Methods ----------
    def has_node(self, node_id):
        return node_id in self._nodes

    def get_all_nodes(self):
        return self._nodes.to_sorted_list()

    def get_node_by_position(self, pos: int):
        return self._find_successor_node_id(pos)

    def get_points(self, node_id):
        points = []

        def _inorder(node):
            if node:
                _inorder(node.left)
                if node.node_id == node_id:
                    points.append(node.position)
                _inorder(node.right)
        _inorder(self._root)
        return points

    def add_node(self, node_id):
        if node_id in self._nodes:
            return False

        self._nodes.add(node_id)
        for j in range(self._v_node):
            position = self._node_position(node_id, j)
            self._root = self._insert_ring_node(
                self._root, position, node_id, j)
            self._point_count += 1
        return True

    def get_node(self, c, s):
        if not self._root:
            return None
        guest_pos = self._guest_position(c, s)
        return self._find_successor_node_id(guest_pos)

    def remove_node(self, node_id):
        if node_id not in self._nodes:
            return False
        if len(self._nodes) == 1:
            return False

        self._nodes.remove(node_id)
        for j in range(self._v_node):
            position = self._node_position(node_id, j)
            self._root = self._delete_ring_node(
                self._root, (position, node_id, j))
            self._point_count -= 1
        return True
