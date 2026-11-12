from core.hash_ring import hash64


class _OrderAVLNode:
    def __init__(self, seq, node_id):
        self.seq = seq
        self.node_id = node_id
        self.left = None
        self.right = None
        self.height = 1
        self.size = 1


class _LookupAVLNode:
    def __init__(self, node_id, seq):
        self.node_id = node_id
        self.seq = seq
        self.left = None
        self.right = None
        self.height = 1


class HashModN:
    def __init__(self, salt=""):
        self._salt = str(salt)
        # ต้นไม้หลักเรียงตามลำดับการเพิ่ม (รองรับ select_by_index)
        self._order_root = None
        self._lookup_root = None  # ต้นไม้ช่วยค้นหา node_id -> seq
        self._next_seq = 0

    @property
    def salt(self):
        return self._salt

    @property
    def node_count(self):
        return self._size(self._order_root)

    def __len__(self):
        return self._size(self._order_root)

    def __contains__(self, node_id):
        return self._find_seq(node_id) is not None

    def __repr__(self):
        return f"HashModN(N={self.node_count}, salt={self._salt!r}, structure='OrderStatisticAVLTree')"

    def _guest_position(self, c, s):
        return hash64(f"{self._salt}guest:{c}:{s}")

    # ---------- Order-Statistic AVL Tree Helpers ----------
    def _height(self, node):
        return node.height if node else 0

    def _size(self, node):
        return node.size if node else 0

    def _update_order_node(self, node):
        node.height = 1 + max(self._height(node.left),
                              self._height(node.right))
        node.size = 1 + self._size(node.left) + self._size(node.right)

    def _balance_factor(self, node):
        return self._height(node.left) - self._height(node.right) if node else 0

    def _rotate_right_order(self, y):
        x = y.left
        t2 = x.right
        x.right = y
        y.left = t2
        self._update_order_node(y)
        self._update_order_node(x)
        return x

    def _rotate_left_order(self, x):
        y = x.right
        t2 = y.left
        y.left = x
        x.right = t2
        self._update_order_node(x)
        self._update_order_node(y)
        return y

    def _rebalance_order(self, node):
        self._update_order_node(node)
        balance = self._balance_factor(node)
        if balance > 1:
            if self._balance_factor(node.left) < 0:
                node.left = self._rotate_left_order(node.left)
            return self._rotate_right_order(node)
        if balance < -1:
            if self._balance_factor(node.right) > 0:
                node.right = self._rotate_right_order(node.right)
            return self._rotate_left_order(node)
        return node

    def _insert_order(self, node, seq, node_id):
        if not node:
            return _OrderAVLNode(seq, node_id)
        if seq < node.seq:
            node.left = self._insert_order(node.left, seq, node_id)
        else:
            node.right = self._insert_order(node.right, seq, node_id)
        return self._rebalance_order(node)

    def _min_order_node(self, node):
        while node.left:
            node = node.left
        return node

    def _delete_order(self, node, seq):
        if not node:
            return None
        if seq < node.seq:
            node.left = self._delete_order(node.left, seq)
        elif seq > node.seq:
            node.right = self._delete_order(node.right, seq)
        else:
            if not node.left:
                return node.right
            if not node.right:
                return node.left
            temp = self._min_order_node(node.right)
            node.seq = temp.seq
            node.node_id = temp.node_id
            node.right = self._delete_order(node.right, temp.seq)
        return self._rebalance_order(node)

    def _select_by_index(self, idx):
        curr = self._order_root
        while curr:
            left_size = self._size(curr.left)
            if idx == left_size:
                return curr.node_id
            elif idx < left_size:
                curr = curr.left
            else:
                idx -= (left_size + 1)
                curr = curr.right
        return None

    # ---------- Lookup AVL Tree Helpers (node_id -> seq) ----------
    def _update_lookup_height(self, node):
        node.height = 1 + max(self._height(node.left),
                              self._height(node.right))

    def _rotate_right_lookup(self, y):
        x = y.left
        t2 = x.right
        x.right = y
        y.left = t2
        self._update_lookup_height(y)
        self._update_lookup_height(x)
        return x

    def _rotate_left_lookup(self, x):
        y = x.right
        t2 = y.left
        y.left = x
        x.right = t2
        self._update_lookup_height(x)
        self._update_lookup_height(y)
        return y

    def _rebalance_lookup(self, node):
        self._update_lookup_height(node)
        balance = self._balance_factor(node)
        if balance > 1:
            if self._balance_factor(node.left) < 0:
                node.left = self._rotate_left_lookup(node.left)
            return self._rotate_right_lookup(node)
        if balance < -1:
            if self._balance_factor(node.right) > 0:
                node.right = self._rotate_right_lookup(node.right)
            return self._rotate_left_lookup(node)
        return node

    def _find_seq(self, node_id):
        curr = self._lookup_root
        while curr:
            if node_id == curr.node_id:
                return curr.seq
            curr = curr.left if node_id < curr.node_id else curr.right
        return None

    def _insert_lookup(self, node, node_id, seq):
        if not node:
            return _LookupAVLNode(node_id, seq)
        if node_id < node.node_id:
            node.left = self._insert_lookup(node.left, node_id, seq)
        else:
            node.right = self._insert_lookup(node.right, node_id, seq)
        return self._rebalance_lookup(node)

    def _min_lookup_node(self, node):
        while node.left:
            node = node.left
        return node

    def _delete_lookup(self, node, node_id):
        if not node:
            return None
        if node_id < node.node_id:
            node.left = self._delete_lookup(node.left, node_id)
        elif node_id > node.node_id:
            node.right = self._delete_lookup(node.right, node_id)
        else:
            if not node.left:
                return node.right
            if not node.right:
                return node.left
            temp = self._min_lookup_node(node.right)
            node.node_id = temp.node_id
            node.seq = temp.seq
            node.right = self._delete_lookup(node.right, temp.node_id)
        return self._rebalance_lookup(node)

    # ---------- Public Methods ----------
    def has_node(self, node_id):
        return node_id in self

    def get_all_nodes(self):
        result = []

        def _inorder(node):
            if node:
                _inorder(node.left)
                result.append(node.node_id)
                _inorder(node.right)
        _inorder(self._lookup_root)
        return result

    def add_node(self, node_id):
        if node_id in self:
            return False
        seq = self._next_seq
        self._next_seq += 1
        self._order_root = self._insert_order(self._order_root, seq, node_id)
        self._lookup_root = self._insert_lookup(
            self._lookup_root, node_id, seq)
        return True

    def get_node(self, c, s):
        n = self.node_count
        if n == 0:
            return None
        hashed = self._guest_position(c, s)
        idx = hashed % n
        return self._select_by_index(idx)

    def remove_node(self, node_id):
        seq = self._find_seq(node_id)
        if seq is None:
            return False
        if self.node_count == 1:
            return False
        self._order_root = self._delete_order(self._order_root, seq)
        self._lookup_root = self._delete_lookup(self._lookup_root, node_id)
        return True
