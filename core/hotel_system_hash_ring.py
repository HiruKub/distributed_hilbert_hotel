class HotelSystemHashRing:
    def __init__(self, N: int, V: int, C: int, s: list[int]):
        if N < 1: raise ValueError("เริ่มระบบด้วยจำนวนอาคารอย่างน้อย 1 (N >= 1)")
        if len(s) != C: raise ValueError("จำนวนช่องทางไม่สัมพันธ์กับจำนวนแขกของแต่ละช่องทาง")
        
        from hash_ring import HashRing
        self.__router = HashRing(V, "hash_ring_salt")

        for i in range(1, N+1): self.__router.add_node(str(i))

        self.__guests_by_id = {}
        self.__guests_by_node = {str(i): set() for i in range(1, N+1)}

        for channel_idx, count in enumerate(s):
            c = channel_idx + 1  # c เริ่มที่ 1
            if count < 0: raise ValueError(f"จำนวนแขกที่เข้าพักของช่องทางที่ {channel_idx} เป็นจำนวนติดลบ")
            for seq in range(1, count + 1):  # s (sequence) เริ่มที่ 1 เสมอ
                self.add_guest(c, seq)

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
