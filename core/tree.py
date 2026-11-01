class AVLNode:
    def __init__(self, key: int, value: tuple[int, int]):
        self.key = key
        self.values = {value}
        self.left = self.right = None
        self.height = 1

    @staticmethod
    def get_height(node):
        return node.height if node else 0

    def set_height(self):
        self.height = 1 + max(self.get_height(self.left), self.get_height(self.right))

    def get_balance(self):
        return self.get_height(self.left) - self.get_height(self.right)

class AVLTree:
    def __init__(self):
        self.root = None

    def __right_rotate(self, root):
        y = root.left
        root.left = y.right
        y.right = root

        root.set_height()
        y.set_height()

        return y

    def __left_rotate(self, root):
        y = root.right
        root.right = y.left
        y.left = root

        root.set_height()
        y.set_height()

        return y

    def insert(self, key, value):
        self.root = self._insert(self.root, key, value)

    def _insert(self, node, key, value):
        if not node: return AVLNode(key, value)

        if key == node.key:
            node.values.add(value)
            return node
        elif key < node.key: node.left = self._insert(node.left, key, value)
        else: node.right = self._insert(node.right, key, value)

        node.set_height()

        return self.__rebalance(node)

    def __rebalance(self, node: AVLNode):
        BF = node.get_balance()

        if BF > 1:
            if node.left.get_balance() < 0: node.left = self.__left_rotate(node.left)
            node = self.__right_rotate(node)
        elif BF < -1:
            if node.right.get_balance() > 0: node.right = self.__right_rotate(node.right)
            node = self.__left_rotate(node)

        return node

    def delete(self, key, value):
        # In-Order Successor
        self.root = self._delete(self.root, key, value)

    def _get_min_node(self, node):
        current = node
        while current.left: current = current.left
        return current

    def _delete(self, node, key, value):
        if not node: return None

        if key < node.key:
            node.left = self._delete(node.left, key, value)
        elif key > node.key:
            node.right = self._delete(node.right, key, value)
        else:
            if value in node.values:
                node.values.remove(value)

            if node.values: return node

            if not node.left: return node.right
            elif not node.right: return node.left

            successor = self._get_min_node(node.right)
            node.key = successor.key
            node.values = successor.values
            node.right = self._delete_node_by_key(node.right, successor.key)

            if not node: return None

            node.set_height()
            return self.__rebalance(node)

    def _delete_node_by_key(self, node, key):
        if not node:
            return None

        if key < node.key:
            node.left = self._delete_node_by_key(node.left, key)
        elif key > node.key:
            node.right = self._delete_node_by_key(node.right, key)
        else:
            if not node.left:
                return node.right
            elif not node.right:
                return node.left

            successor = self._get_min_node(node.right)
            node.key = successor.key
            node.values = successor.values
            node.right = self._delete_node_by_key(node.right, successor.key)

        if not node:
            return None

        node.set_height()
        return self.__rebalance(node)




def is_balanced(node: AVLNode | None) -> bool:
    """ตรวจสอบว่าทุก Node ใน Tree มี Balance Factor อยู่ในช่วง [-1, 1] หรือไม่"""
    if not node:
        return True
    if abs(node.get_balance()) > 1:
        return False
    return is_balanced(node.left) and is_balanced(node.right)

def get_inorder_keys(node: AVLNode | None) -> list[int]:
    """ดึง Key ทั้งหมดใน Tree ออกมาตามลำดับน้อยไปมาก (In-order Traversal)"""
    if not node:
        return []
    return get_inorder_keys(node.left) + [node.key] + get_inorder_keys(node.right)

# --- สคริปต์ทดสอบ AVLTree Delete ---
