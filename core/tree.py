class AVLNode:
    def __init__(self, key: int, value: tuple[int, int]):
        self.key = key
        self.values = set(tuple[int, int]) = {value}
        self.height = self.set_height()
        self.left = self.right = None

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