import argparse
import math
import os
import statistics
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiments.run_experiments import (FIELDS_A, FIELDS_B, FIELDS_C, MOD_N, RING,  # noqa: E402
                                         RESULTS_DIR, build_hotel_timed, run_b_case)
from utils.reports import load_stats  # noqa: E402

results = []


def check(ok, text):
    results.append(("PASS" if ok else "FAIL", text))


def info(text):
    results.append(("INFO", text))


def close(a, b, tol=1e-6):
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def load(results_dir, name, fields):
    path = os.path.join(results_dir, f"experiment_{name}_results.csv")
    if not os.path.exists(path):
        check(False, f"{name}: ไม่พบไฟล์ {path}")
        return None
    df = pd.read_csv(path)
    check(list(df.columns) == fields, f"{name}: คอลัมน์ครบและเรียงตามที่กำหนด")
    return df


# ---------------------------------------------------------------- A
def verify_a(df):
    ks = sorted(df["K"].unique())
    check(len(df) == len(ks) * 3, f"A: จำนวนแถว {len(df)} = {len(ks)} ค่า K x 3 salt")
    check(all(df.groupby("K")["salt"].nunique() == 3), "A: ทุก K มีครบ 3 salt")
    nulls = df.isna().sum().sum()
    check(nulls == 0, f"A: ไม่มีค่าว่าง (พบ {nulls})")
    time_cols = ["t_build_ring_s", "t_place_guests_s", "t_sort_s",
                 "t_search_by_id_us", "t_search_by_room_us", "t_route_only_us"]
    check(bool((df[time_cols] > 0).all().all()), "A: ค่าเวลาทุกตัวเป็นบวก")
    check(bool((df["mem_peak_mib"] >= df["mem_current_mib"]).all()),
          "A: หน่วยความจำ peak >= current ทุกแถว")
    med = df.groupby("K")[["t_place_guests_s", "t_sort_s", "mem_current_mib"]].median()
    check(all(med[c].is_monotonic_increasing for c in med.columns),
          "A: เวลาจัดแขก เวลาเรียง และหน่วยความจำ เพิ่มขึ้นตาม K")
    # search_by_id อ่านจาก dict (ไม่แตะวงแหวน) จึงควรเร็วกว่าการคำนวณอาคารจากวงแหวน (SHA-256 + bisect)
    check(bool((df["t_search_by_id_us"] < df["t_route_only_us"]).all()),
          "A: ค้นด้วยรหัสแขก (อ่าน dict) เร็วกว่าคำนวณอาคารจากวงแหวน (แฮช + binary search) ตรงกับโค้ดจริง")
    if len(ks) >= 2:
        ratio = med.loc[ks[-1], "t_place_guests_s"] / med.loc[ks[0], "t_place_guests_s"]
        info(f"A: K เพิ่ม {ks[-1] / ks[0]:.0f} เท่า เวลาจัดแขกเพิ่ม {ratio:.1f} เท่า "
             "(ถ้าใกล้กัน = เกือบเชิงเส้น)")


# ---------------------------------------------------------------- B
def verify_b(df):
    ns = sorted(df["N"].unique())
    expect_rows = len(ns) * 3 * 2 * 2
    check(len(df) == expect_rows, f"B: จำนวนแถว {len(df)} = {len(ns)} N x 3 salt x 2 วิธี x 2 คำสั่ง")
    check(df.isna().sum().sum() == 0, "B: ไม่มีค่าว่าง")
    recomputed = df["migrated_count"] / df["K"]
    check(bool(all(close(a, b, 1e-5) for a, b in zip(recomputed, df["migration_rate"]))),
          "B: migration_rate = migrated_count / K ตรงทุกแถว")
    check(bool((df["total_guests_after"] == df["K"]).all()), "B: จำนวนแขกรวมไม่หายไม่เพิ่ม")
    check(bool(df["index_consistent"].all()), "B: ดัชนีสองชุดสอดคล้องกับวงแหวนทุกแถว")

    ring = df[df["method"] == "ring"]
    mod = df[df["method"] == "mod_n"]
    check(bool(ring["only_expected_nodes_move"].all()),
          "B: ring เพิ่มอาคาร -> ย้ายเข้าอาคารใหม่เท่านั้น / ลบ -> ย้ายเฉพาะแขกของอาคารที่ลบ")
    check(not bool(mod["only_expected_nodes_move"].any()),
          "B: mod N ย้ายแขกข้ามอาคารที่ไม่เกี่ยวข้อง (ตรงข้ามกับ ring)")
    check(bool((mod["migration_rate"] > 0.5).all()),
          "B: mod N อัตราย้ายมากกว่า 50% ทุกแถว (ย้ายเกือบหมด)")
    check(bool((ring["migration_rate"] < 0.35).all()),
          "B: ring อัตราย้ายต่ำกว่า 35% ทุกแถว")

    gap = (ring.groupby(["N", "operation"])
           .agg(rate=("migration_rate", "mean"), exp=("expected_rate", "mean")))
    gap["diff"] = (gap["rate"] - gap["exp"]).abs()
    worst = gap["diff"].max()
    check(worst < 0.05, f"B: ค่าเฉลี่ย 3 รอบของ ring ห่างจากทฤษฎีไม่เกิน 0.05 (ห่างสุด {worst:.4f})")
    info("B: ค่าที่ต่างจากทฤษฎีเป็นเรื่องปกติ ผลขึ้นกับตำแหน่งแฮช (ดู 4.4 ของโจทย์)")


# ---------------------------------------------------------------- C
def verify_c(df):
    vs = sorted(df["V"].unique())
    check(len(df) == len(vs) * 3, f"C: จำนวนแถว {len(df)} = {len(vs)} ค่า V x 3 salt")
    check(df[[c for c in df.columns if c != "guests_per_node"]].isna().sum().sum() == 0,
          "C: ไม่มีค่าว่าง")
    check(bool((df["ring_points"] == df["N"] * df["V"]).all()), "C: ring_points = N x V")

    ok_sum = ok_stats = True
    for _, r in df.iterrows():
        counts = [int(x.split(":")[1]) for x in r["guests_per_node"].split(";")]
        ok_sum &= (sum(counts) == r["K"] and len(counts) == r["N"])
        mean = statistics.fmean(counts)
        std = statistics.pstdev(counts)
        ok_stats &= (r["max"] == max(counts) and r["min"] == min(counts)
                     and close(r["mean"], mean, 1e-3) and close(r["std"], std, 1e-3)
                     and close(r["cv"], std / mean, 1e-3))
    check(ok_sum, "C: แขกต่ออาคารรวมกันได้ K และมีครบ N อาคาร (รวมอาคารที่มี 0 คน)")
    check(ok_stats, "C: max / min / mean / std / CV คำนวณซ้ำจากแขกต่ออาคารแล้วตรงกับที่บันทึก")

    cv = df.groupby("V")["cv"].mean()
    check(bool(cv.is_monotonic_decreasing), f"C: CV เฉลี่ยลดลงเมื่อ V เพิ่ม ({', '.join(f'V={v}: {c:.3f}' for v, c in cv.items())})")
    ring_mem = df.groupby("V")["mem_ring_current_mib"].mean()
    check(bool(ring_mem.is_monotonic_increasing), "C: หน่วยความจำของวงแหวนเพิ่มขึ้นเมื่อ V เพิ่ม")
    check(bool((df["mem_total_peak_mib"] >= df["mem_total_current_mib"]).all()),
          "C: หน่วยความจำ peak >= current ทุกแถว")


# ---------------------------------------------------------------- คำนวณซ้ำ
def recompute(b_df, c_df):
    mismatches = 0
    cases = b_df[["N", "V", "K", "salt"]].drop_duplicates().head(4)
    for _, c in cases.iterrows():
        for mode, name in ((RING, "ring"), (MOD_N, "mod_n")):
            fresh = run_b_case(int(c.N), int(c.V), int(c.K), mode, str(c.salt))
            for row in fresh:
                old = b_df[(b_df.N == c.N) & (b_df.salt == c.salt) & (b_df.method == name)
                           & (b_df.operation == row["operation"])].iloc[0]
                if old["migrated_count"] != row["migrated_count"]:
                    mismatches += 1
    check(mismatches == 0,
          f"คำนวณซ้ำ B ({len(cases)} เงื่อนไข x 2 วิธี x 2 คำสั่ง): จำนวนย้ายเท่า CSV ทุกค่า")

    # C: คำนวณแขกต่ออาคารซ้ำ
    bad = 0
    sample = c_df[["N", "V", "K", "salt"]].drop_duplicates().iloc[[0, -1]]
    for _, c in sample.iterrows():
        hotel, _, _ = build_hotel_timed(int(c.N), int(c.V), int(c.K), RING, str(c.salt))
        text = ";".join(f"{n}:{k}" for n, k in load_stats(hotel).counts)
        old = c_df[(c_df.V == c.V) & (c_df.salt == c.salt)].iloc[0]["guests_per_node"]
        bad += (text != old)
    check(bad == 0, f"คำนวณซ้ำ C ({len(sample)} เงื่อนไข): แขกต่ออาคารตรงกับ CSV ทุกอาคาร")

    # แฮชคงที่ข้ามการรัน
    from core.hash_ring import hash64
    h1, h2 = hash64("guest:1:1"), hash64("guest:1:1")
    check(h1 == h2, f"hash64('guest:1:1') ได้ค่าเดิมเสมอ ({h1}) บันทึกค่านี้ไว้เทียบหลังเปิดโปรแกรมใหม่")


def main(argv=None):
    parser = argparse.ArgumentParser(description="ตรวจความถูกต้องของผลการทดลอง")
    parser.add_argument("--results", default=RESULTS_DIR)
    parser.add_argument("--no-recompute", action="store_true")
    args = parser.parse_args(argv)

    a = load(args.results, "A", FIELDS_A)
    b = load(args.results, "B", FIELDS_B)
    c = load(args.results, "C", FIELDS_C)
    if a is not None: verify_a(a)
    if b is not None: verify_b(b)
    if c is not None: verify_c(c)
    if not args.no_recompute and b is not None and c is not None:
        recompute(b, c)

    for status, text in results:
        print(f"[{status}] {text}")
    fails = sum(1 for s, _ in results if s == "FAIL")
    passes = sum(1 for s, _ in results if s == "PASS")
    print(f"\nสรุป: ผ่าน {passes} / ไม่ผ่าน {fails}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
