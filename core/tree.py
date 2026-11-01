class AVLNode:
    def __init__(self, key: int, value: tuple[int, int]):
        self.key = key
        self.values = set(tuple[int, int]) = {value}
        self.height = self.set_height()
        self.left = self.right = None

    def set_height(self):
        left_h = self.left.height if self.left else 0
        right_h = self.right.height if self.right else 0
        self.height = 1 + max(left_h, right_h)

    def get_balance(self):
        left_h = self.left.height if self.left else 0
        right_h = self.right.height if self.right else 0
        return left_h - right_h

class AVLTree:
    ...