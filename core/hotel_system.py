class HotelSystem:
    def __init__(self, method):
        self.__method = method
        self.__guests = dict()
        self.__room_id = dict()

    @property
    def guest_count(self): return len(self.__guests)

    @property
    def all_room_no(self): return [g.room_no for g in self.__guests.values()]

    @property
    def point_count(self): return self.__method.point_count

    def add_building(self, node_id: str):
        if not isinstance(node_id, str): return False

        result = self.__method.add_node(node_id)
        if not result: return False

        return True

    def add_guest(self, c, s):
        if (c, s) in self.__guests: return False

        try:
            node_id = self.__method.get_node(c, s)
            if node_id is None: return False

            from guest import Guest
            guest = Guest(c, s, node_id)

            self.__guests[(c, s)] = guest
            self.__room_id[(node_id, guest.room_no)] = (c, s)

            return True
        except: return False

    def get_guest_from_c_s(self, c, s): return self.__guests[(c, s)]
    def get_guest_from_node_room(self, node_id, room_no): 
        return self.__room_id[(node_id, room_no)]

if __name__ == "__main__":
    from hash_ring import HashRing

    virtual_node_count = 32
    ring = HashRing(virtual_node_count)
    hs = HotelSystem(ring)
    print(f'{"-"*5} Add Building Test {"-"*5}')
    print(f'#1: {hs.add_building("A")}\t| expected: True') # Normal
    print(f'#2: {hs.add_building("B")}\t| expected: True') # Different Name
    print(f'#3: {hs.add_building("A")}\t| expected: False') # Duplicate Name
    print(f'#4: {hs.add_building(1)}\t| expected: False') # Invalid Input
    print(f'#5: {hs.point_count}\t \t| expected: {virtual_node_count * 2}') # point count
    print()

    virtual_node_count = 32
    ring = HashRing(virtual_node_count)
    hs = HotelSystem(ring)
    print(f'{"-"*5} Add Guest Test {"-"*5}')
    print(f'#1: {hs.add_guest(1, 1)}\t| expected: False') # No Building
    
    hs.add_building("A")
    print(f'#2: {hs.add_guest(1, 1)}\t| expected: True') # Normal
    print(f'#3: {hs.add_guest(1, 1)}\t| expected: False') # Duplicate
    print(f'#4: {hs.add_guest(1, 2)}\t| expected: True') # Add more
    print(f'#5: {hs.add_guest(2, 1)}\t| expected: True') # Add more
    print(f'#6: {hs.guest_count}\t\t| expected: 3') # Count Guest
    print(f'#7: {hs.all_room_no}\t| expected: 3 distinct room no') # room no

    test_guest = hs.get_guest_from_c_s(2, 1)
    print(f'#8: {hs.get_guest_from_node_room(test_guest.node_id, test_guest.room_no)}\t| expected: (2, 1)') # test consistency