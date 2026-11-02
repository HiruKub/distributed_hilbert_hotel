class HotelSystemHashRing:
    def __init__(self, N: int, V: int, C: int, s: list[int]):
        self.__validate_init_params(N, C, s)
                
        from hash_ring import HashRing
        self.__router = HashRing(V, "hash_ring_salt")
        self.__guests_by_id = {}
        self.__guests_by_node = {}

        self.__init_nodes(N)
        self.__init_guests(s)

    def __validate_init_params(self, N: int, C: int, s: list[int]):
        if N < 1: 
            raise ValueError("เริ่มระบบด้วยจำนวนอาคารอย่างน้อย 1 (N >= 1)")
        if len(s) != C: 
            raise ValueError("จำนวนช่องทางไม่สัมพันธ์กับจำนวนแขกของแต่ละช่องทาง")
    def __init_nodes(self, N):
        for i in range(1, N+1):
            node_id = str(i)
            self.__router.add_node(node_id)
            self.__guests_by_node[node_id] = set()
    def __init_guests(self, s: list[int]):
        for channel_idx, count in enumerate(s):
            c = channel_idx + 1  # c เริ่มที่ 1
            if count < 0: raise ValueError(f"จำนวนแขกที่เข้าพักของช่องทางที่ {channel_idx} เป็นจำนวนติดลบ")
            for seq in range(1, count + 1):  # s (sequence) เริ่มที่ 1 เสมอ
                self.add_guest(c, seq)

    @property
    def N(self): return self.__N
    @property
    def V(self): return self.__V
    @property
    def C(self): return self.__C
    @property
    def s(self): return self.__s
    @property
    def guests_by_id(self): return self.__guests_by_id
    @property
    def guests_by_node(self): return self.__guests_by_node
    @property
    def router(self): return self.__router

    # Method
    def add_guest(self, c: int, s: int):
        node_id = self.__router.get_node(c, s)

        # duplicate 
        if (c, s) in self.__guests_by_id.keys(): raise ValueError(f"มีการเพิ่มแขก ({c},{s})ในระบบแล้ว")
        
        # บันทึกลง Primary Index
        from guest import Guest
        self.__guests_by_id[(c, s)] = Guest(c, s, node_id)

        # บันทึกลง Secondary Index
        if node_id not in self.__guests_by_node:
            self.__guests_by_node[node_id] = set()
        self.__guests_by_node[node_id].add((c, s))

        return True
    def add_guest_group(self, c: int, s_start: int, count: int):
        if not isinstance(c, int) or c < 1:
            raise ValueError("หมายเลขช่องทาง c ต้องเป็นจำนวนเต็ม >= 1")
        if not isinstance(s_start, int) or s_start < 1:
            raise ValueError("ลำดับเริ่มต้น s_start ต้องเป็นจำนวนเต็ม >= 1")
        if not isinstance(count, int) or count < 0:
            raise ValueError("จำนวนแขก count ต้องไม่ติดลบ")

        if count == 0: return True

        target_range = range(s_start, s_start + count)
        for s in target_range:
            if (c, s) in self.__guests_by_id: 
                raise ValueError("ในช่วงมีแขกที่รหัสทับกับแขกที่มีอยู่ ไม่สามารถเพิ่มแขกได้ทั้งกลุ่ม")
        for s in target_range: self.add_guest(c, s)

        return True
    def remove_guest(self, c: int, s: int):
        if not isinstance(c, int) or c < 1:
            raise ValueError("หมายเลขช่องทาง c ต้องเป็นจำนวนเต็ม >= 1")
        if not isinstance(s, int) or s < 1:
            raise ValueError("ลำดับ s ต้องเป็นจำนวนเต็ม >= 1")
        if (c, s) not in self.__guests_by_id:
            raise ValueError("ไม่มีแขกในระบบ")

        node_id = self.__router.get_node(c, s)

        del self.__guests_by_id[(c, s)]
        if node_id in self.__guests_by_node:
            self.__guests_by_node[node_id].remove((c, s))

        return True

    def search_by_id(self, c, s):
        if not isinstance(c, int) or c < 1:
            raise ValueError("หมายเลขช่องทาง c ต้องเป็นจำนวนเต็ม >= 1")
        if not isinstance(s, int) or s < 1:
            raise ValueError("ลำดับ s ต้องเป็นจำนวนเต็ม >= 1")

        result = self.__guests_by_id[(c, s)]
        if not result: raise ValueError("ไม่พบรหัสแขกที่ค้นหา")

        return result.node_id, result.room_no
    def search_by_node_room(self, node_id, room_no):
        if node_id not in self.__guests_by_node:
            raise ValueError(f"ไม่พบ Node ID '{node_id}' ในระบบ")

        import math
        z_prime = room_no - 1
        w = int((math.isqrt(8 * z_prime + 1) - 1) // 2)
        t = (w * (w + 1)) // 2
        b = z_prime - t
        a = w - b

        c = a + 1
        s = b + 1

        result = self.__guests_by_id.get((c, s))
        if result and result.node_id == node_id: 
            return result.c, result.s

        raise ValueError(f"ไม่พบแขกที่ค้นหา")

    def add_node(self, node_id: str):
        if node_id in self.__guests_by_node:
            raise ValueError("มีอาคารนี้อยู่ในระบบแล้ว")

        affected_nodes = set()
        for j in range(self.__router.v_node):
            position = self.__router._node_position(node_id, j)
            successor_node = self.__router.get_node_by_position(position)
            if successor_node and successor_node != node_id:
                affected_nodes.add(successor_node)

        self.__router.add_node(node_id)
        self.__guests_by_node[node_id] = set()

        for target_node in affected_nodes:
            current_guests = list(self.__guests_by_node[target_node])
            for c, s in current_guests:
                if self.__router.get_node(c, s) == node_id:
                    self.__guests_by_node[target_node].remove((c, s))
                    self.__guests_by_node[node_id].add((c, s))
                    self.__guests_by_id[(c, s)].node_id = node_id

        return True