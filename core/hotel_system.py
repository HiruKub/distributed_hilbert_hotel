class HotelSystem:
    def __init__(self, method):
        self.__method = method
        self.__guests = dict()
        self.__room_id = dict()

    @property
    def point_count(self): return self.__method.point_count

    def add_building(self, node_id: str):
        if not isinstance(node_id, str): return False

        result = self.__method.add_node(node_id)
        if not result: return False

        return True

if __name__ == "__main__":
    from hash_ring import HashRing

    virtual_node_count = 32
    hs = HotelSystem(HashRing(virtual_node_count))

    print(f'{"-"*5} Add Building Test {"-"*5}')
    print(f'#1: {hs.add_building("A")}\t| expected: True') # Normal
    print(f'#2: {hs.add_building("B")}\t| expected: True') # Different Name
    print(f'#3: {hs.add_building("A")}\t| expected: False') # Duplicate Name
    print(f'#4: {hs.add_building(1)}\t| expected: False') # Invalid Input
    print(f'#5: {hs.point_count}\t \t| expected: {virtual_node_count * 2}') # point count
    print()