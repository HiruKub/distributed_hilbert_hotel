import csv
import os

from utils.reports import list_rooms

GUEST_FIELDS = ["channel_id", "sequence_id", "node_id", "room_no"]
MIGRATION_FIELDS = ["channel_id", "sequence_id", "old_node", "new_node", "room_no"]


def write_csv(path, fieldnames, rows, encoding="utf-8"):
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    count = 0
    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def export_guests(hotel, path, encoding="utf-8"):
    rows = ({"channel_id": r.c, "sequence_id": r.s, "node_id": r.node_id, "room_no": r.room_no}
            for r in list_rooms(hotel))
    return write_csv(path, GUEST_FIELDS, rows, encoding)


def export_migrations(report, path, encoding="utf-8"):
    rows = ({"channel_id": m.guest_id[0], "sequence_id": m.guest_id[1], "old_node": m.old_node, "new_node": m.new_node, "room_no": m.room_no}
            for m in report.migrations)
    return write_csv(path, MIGRATION_FIELDS, rows, encoding)
