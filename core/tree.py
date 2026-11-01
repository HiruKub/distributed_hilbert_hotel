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