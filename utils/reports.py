import statistics
from collections import namedtuple
from dataclasses import dataclass, field

RoomRow = namedtuple("RoomRow", ["node_id", "room_no", "c", "s"])


def node_sort_key(node_id):
    try:
        return (0, int(node_id), str(node_id))
    except (TypeError, ValueError):
        return (1, 0, str(node_id))


def sorted_node_ids(hotel):
    return sorted(hotel.guests_by_node, key=node_sort_key)


def list_rooms(hotel):
    rows = [RoomRow(g.node_id, g.room_no, g.c, g.s)
            for g in hotel.guests_by_id.values()]
    rows.sort(key=lambda r: (node_sort_key(r.node_id), r.room_no))
    return rows


@dataclass
class LoadStats:
    counts: list = field(default_factory=list)
    total: int = 0
    node_count: int = 0
    maximum: float = 0
    minimum: float = 0
    mean: float = 0.0
    std: float = 0.0
    cv: object = None


def load_stats(hotel):
    counts = [(n, len(hotel.guests_by_node[n])) for n in sorted_node_ids(hotel)]
    values = [c for _, c in counts]
    total = sum(values)
    stats = LoadStats(counts=counts, total=total, node_count=len(values))
    if not values or total == 0:
        return stats
    stats.maximum = max(values)
    stats.minimum = min(values)
    stats.mean = total / len(values)
    stats.std = statistics.pstdev(values)
    stats.cv = stats.std / stats.mean
    return stats


def verify_consistency(hotel):
    problems = []
    by_id = hotel.guests_by_id
    by_node = hotel.guests_by_node

    indexed = 0
    for node_id, members in by_node.items():
        for key in members:
            indexed += 1
            guest = by_id.get(key)
            if guest is None:
                problems.append(f"{key} อยู่ในอาคาร {node_id} แต่ไม่มีใน guests_by_id")
            elif guest.node_id != node_id:
                problems.append(f"{key} อยู่ในอาคาร {node_id} แต่ Guest.node_id={guest.node_id}")
    if indexed != len(by_id):
        problems.append(f"จำนวนในดัชนีอาคาร ({indexed}) ไม่เท่ากับ guests_by_id ({len(by_id)})")

    for (c, s), guest in by_id.items():
        expected = hotel.router.get_node(c, s)
        if guest.node_id != expected:
            problems.append(f"{(c, s)} เก็บอาคาร {guest.node_id} แต่วงแหวนคำนวณได้ {expected}")
    return problems
