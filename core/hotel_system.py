class HotelSystem:
    def __init__(self, num_buildings, num_rooms_per_building, method):
        from tree import AVLTree
        self.__B = num_buildings
        self.__S = num_rooms_per_building
        self.__method = method
        self.__hash_ring_tree = AVLTree()
        self.__guests = {}
        self.__room_id = {}

if __name__ == "__main__":
    ...
    # from hash_ring import HashRing

    # virtual_node_count = 32
    # ring = HashRing(virtual_node_count)
    # hs = HotelSystem(ring)
    # print(f'{"-"*5} Add Building Test {"-"*5}')
    # print(f'#1: {hs.add_building("A")}\t| expected: True') # Normal
    # print(f'#2: {hs.add_building("B")}\t| expected: True') # Different Name
    # print(f'#3: {hs.add_building("A")}\t| expected: False') # Duplicate Name
    # print(f'#4: {hs.add_building(1)}\t| expected: False') # Invalid Input
    # print(f'#5: {hs.point_count}\t \t| expected: {virtual_node_count * 2}') # point count
    # print()

    # virtual_node_count = 32
    # ring = HashRing(virtual_node_count)
    # hs = HotelSystem(ring)
    # print(f'{"-"*5} Add Guest Test {"-"*5}')
    # print(f'#1: {hs.add_guest(1, 1)}\t| expected: False') # No Building
    
    # hs.add_building("A")
    # print(f'#2: {hs.add_guest(1, 1)}\t| expected: True') # Normal
    # print(f'#3: {hs.add_guest(1, 1)}\t| expected: False') # Duplicate
    # print(f'#4: {hs.add_guest(1, 2)}\t| expected: True') # Add more
    # print(f'#5: {hs.add_guest(2, 1)}\t| expected: True') # Add more
    # print(f'#6: {hs.guest_count}\t\t| expected: 3') # Count Guest
    # print(f'#7: {hs.all_room_no}\t| expected: 3 distinct room no') # room no

    # test_guest = hs.search_by_guest(2, 1)
    # print(f'#8: {hs.search_by_room(test_guest.node_id, test_guest.room_no)}\t| expected: (2, 1)') # test consistency

