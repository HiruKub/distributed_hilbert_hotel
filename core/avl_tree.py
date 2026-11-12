"""
core/avl_tree.py
โมดูลโครงสร้างข้อมูล Self-Balancing AVL Tree ส่วนกลางสำหรับระบบ Distributed Hilbert's Hotel
ประกอบด้วย:
1. _BaseAVLTree         : คลาสฐานรวมกลไกการคำนวณความสูง การหมุนต้นไม้ (Rotation) และการปรับสมดุล
2. AVLTreeMap           : โครงสร้างข้อมูล Key-Value Map (ใช้แทน dict) รองรับค้นหาค่าเพดาน (Ceil/Successor)
3. AVLTreeSet           : โครงสร้างข้อมูล Set (ใช้แทน set) พัฒนาต่อยอดจาก AVLTreeMap
4. OrderStatisticAVLTree: ต้นไม้ AVL แบบเก็บขนาดต้นไม้ย่อย (Subtree Size) รองรับการเข้าถึงด้วย Index O(log N)
"""


class _AVLMapNode:
    __slots__ = ("key", "value", "left", "right", "height")

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None
        self.height = 1


class _BaseAVLTree:
    def _height(self, node):
        return node.height if node else 0

    def _balance_factor(self, node):
        return self._height(node.left) - self._height(node.right) if node else 0

    def _update_node(self, node):
        node.height = 1 + max(self._height(node.left), self._height(node.right))

    def _rotate_right(self, y):
        x = y.left
        t2 = x.right
        x.right = y
        y.left = t2
        self._update_node(y)
        self._update_node(x)
        return x

    def _rotate_left(self, x):
        y = x.right
        t2 = y.left
        y.left = x
        x.right = t2
        self._update_node(x)
        self._update_node(y)
        return y

    def _rebalance(self, node):
        self._update_node(node)
        balance = self._balance_factor(node)

        # Left-Heavy
        if balance > 1:
            if self._balance_factor(node.left) < 0:
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)

        # Right-Heavy
        if balance < -1:
            if self._balance_factor(node.right) > 0:
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)

        return node

    def _min_node(self, node):
        curr = node
        while curr and curr.left:
            curr = curr.left
        return curr


class AVLTreeMap(_BaseAVLTree):

    def __init__(self):
        self._root = None
        self._size = 0

    def __len__(self):
        return self._size

    def __bool__(self):
        return self._size > 0

    def __contains__(self, key):
        return self._find_node(key) is not None

    def __getitem__(self, key):
        node = self._find_node(key)
        if not node:
            raise KeyError(key)
        return node.value

    def __setitem__(self, key, value):
        node = self._find_node(key)
        if node:
            node.value = value
        else:
            self._root = self._insert(self._root, key, value)
            self._size += 1

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        self._root = self._delete(self._root, key)
        self._size -= 1

    def __iter__(self):
        return iter(self.keys())

    def get(self, key, default=None):
        node = self._find_node(key)
        return node.value if node else default

    def keys(self):
        result = []
        self._inorder_keys(self._root, result)
        return result

    def values(self):
        result = []
        self._inorder_values(self._root, result)
        return result

    def items(self):
        result = []
        self._inorder_items(self._root, result)
        return result

    def find_ceil_or_first(self, target_key):
        if not self._root:
            return None

        curr = self._root
        candidate = None
        while curr:
            if curr.key >= target_key:
                candidate = curr
                curr = curr.left
            else:
                curr = curr.right

        if candidate is None:
            candidate = self._min_node(self._root)

        return candidate.key, candidate.value

    def _find_node(self, key):
        curr = self._root
        while curr:
            if key == curr.key:
                return curr
            curr = curr.left if key < curr.key else curr.right
        return None

    def _insert(self, node, key, value):
        if not node:
            return _AVLMapNode(key, value)
        if key < node.key:
            node.left = self._insert(node.left, key, value)
        else:
            node.right = self._insert(node.right, key, value)
        return self._rebalance(node)

    def _delete(self, node, key):
        if not node:
            return None
        if key < node.key:
            node.left = self._delete(node.left, key)
        elif key > node.key:
            node.right = self._delete(node.right, key)
        else:
            if not node.left:
                return node.right
            if not node.right:
                return node.left
            temp = self._min_node(node.right)
            node.key = temp.key
            node.value = temp.value
            node.right = self._delete(node.right, temp.key)
        return self._rebalance(node)

    def _inorder_keys(self, node, result):
        if node:
            self._inorder_keys(node.left, result)
            result.append(node.key)
            self._inorder_keys(node.right, result)

    def _inorder_values(self, node, result):
        if node:
            self._inorder_values(node.left, result)
            result.append(node.value)
            self._inorder_values(node.right, result)

    def _inorder_items(self, node, result):
        if node:
            self._inorder_items(node.left, result)
            result.append((node.key, node.value))
            self._inorder_items(node.right, result)


class AVLTreeSet:
    def __init__(self):
        self._map = AVLTreeMap()

    def __len__(self):
        return len(self._map)

    def __bool__(self):
        return bool(self._map)

    def __contains__(self, item):
        return item in self._map

    def __iter__(self):
        return iter(self._map.keys())

    def add(self, item):
        self._map[item] = True

    def remove(self, item):
        if item not in self._map:
            raise KeyError(item)
        del self._map[item]

    def discard(self, item):
        if item in self._map:
            del self._map[item]

    def to_list(self):
        return self._map.keys()


class _OrderAVLNode:
    __slots__ = ("seq", "value", "left", "right", "height", "size")

    def __init__(self, seq, value):
        self.seq = seq
        self.value = value
        self.left = None
        self.right = None
        self.height = 1
        self.size = 1


class OrderStatisticAVLTree(_BaseAVLTree):
    def __init__(self):
        self._order_root = None
        self._lookup_map = AVLTreeMap()  # map: value (node_id) -> seq
        self._next_seq = 0

    def __len__(self):
        return len(self._lookup_map)

    def __bool__(self):
        return len(self._lookup_map) > 0

    def __contains__(self, value):
        return value in self._lookup_map

    def _size(self, node):
        return node.size if node else 0

    def _update_node(self, node):
        node.height = 1 + max(self._height(node.left), self._height(node.right))
        node.size = 1 + self._size(node.left) + self._size(node.right)

    def append(self, value):
        if value in self._lookup_map:
            return False
        seq = self._next_seq
        self._next_seq += 1
        self._order_root = self._insert_order(self._order_root, seq, value)
        self._lookup_map[value] = seq
        return True

    def remove(self, value):
        seq = self._lookup_map.get(value)
        if seq is None:
            return False
        self._order_root = self._delete_order(self._order_root, seq)
        del self._lookup_map[value]
        return True

    def get_by_index(self, idx: int):
        curr = self._order_root
        while curr:
            left_size = self._size(curr.left)
            if idx == left_size:
                return curr.value
            if idx < left_size:
                curr = curr.left
            else:
                idx -= (left_size + 1)
                curr = curr.right
        return None

    def get_sorted_values(self):
        return self._lookup_map.keys()

    def _insert_order(self, node, seq, value):
        if not node:
            return _OrderAVLNode(seq, value)
        if seq < node.seq:
            node.left = self._insert_order(node.left, seq, value)
        else:
            node.right = self._insert_order(node.right, seq, value)
        return self._rebalance(node)

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
            temp = self._min_node(node.right)
            node.seq = temp.seq
            node.value = temp.value
            node.right = self._delete_order(node.right, temp.seq)
        return self._rebalance(node)