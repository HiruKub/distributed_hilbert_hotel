class HotelSystem:
    def __init__(self, num_buildings, num_rooms_per_building, method):
        from tree import AVLTree
        self.__B = num_buildings
        self.__S = num_rooms_per_building
        self.__method = method
        self.__hash_tree = AVLTree()
        self.__guests = {}
        self.__room_id = {}

    @property
    def method(self): return self.__method

    def add_guest(self, c, s, room_index) -> None:
        guest = (c, s)
        self.__guests[guest] = room_index
        self.__room_id[room_index] = guest

        from hash_ring import hash64
        guest_hash = hash64(f"{self.__method.salt}guest:{c}:{s}")
        self.__hash_tree.insert(guest_hash, guest)

    def add_building(self, node_id):
        added = self.__method.add_node(node_id)
        if not added:
            return []

        relocated_guests = []

        if hasattr(self.__method, "_ring"):
            if self.__method.node_count == 1:
                all_guests = self.__hash_tree.range_query(-1, (1 << 64) - 1)
                return [(guest, node_id) for guest in all_guests]

            ring_list = self.__method._ring
            visited_guests = set()

            for idx, (pos, nid, j) in enumerate(ring_list):
                if nid == node_id:
                    prev_pos = ring_list[idx - 1][0] if idx > 0 else ring_list[-1][0]
                    
                    if prev_pos == pos:
                        guests_in_range = self.__hash_tree.range_query(-1, (1 << 64) - 1)
                    else:
                        guests_in_range = self.__hash_tree.range_query(prev_pos, pos)
                    
                    for guest in guests_in_range:
                        if guest not in visited_guests:
                            visited_guests.add(guest)
                            target_node = self.__method.get_node(guest[0], guest[1])
                            if target_node == node_id:
                                relocated_guests.append((guest, target_node))

        else:
            for guest in list(self.__guests.keys()):
                target_node = self.__method.get_node(guest[0], guest[1])
                if target_node == node_id:
                    relocated_guests.append((guest, target_node))

        return relocated_guests
if __name__ == "__main__":
    ...
