import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESULTS = os.path.join(HERE, "resultsTree")
DEFAULT_OUT = os.path.join(HERE, "resultsTree")


def _agg(df, x, y):
    g = df.groupby(x)[y].agg(["mean", "min", "max"]).reset_index()
    return g


def _errplot(ax, df, x, y, label, marker="o", linestyle="-"):
    g = _agg(df, x, y)
    yerr = [(g["mean"] - g["min"]).clip(lower=0), (g["max"] - g["mean"]).clip(lower=0)]
    ax.errorbar(g[x], g["mean"], yerr=yerr, marker=marker, linestyle=linestyle,
                capsize=3, label=label)


def _rounds_text(df):
    salts = sorted(df["salt"].astype(str).unique())
    return f"{len(salts)} rounds (salt {', '.join(salts)}); marker = mean, bar = min-max"


def plot_a(results_dir, out_dir):
    df = pd.read_csv(os.path.join(results_dir, "experiment_A_results.csv"))
    N, V = int(df["N"].iloc[0]), int(df["V"].iloc[0])
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))

    ax = axes[0]
    _errplot(ax, df, "K", "t_build_ring_s", "build ring")
    _errplot(ax, df, "K", "t_place_guests_s", "place guests")
    _errplot(ax, df, "K", "t_sort_s", "sort rooms")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Number of guests K"); ax.set_ylabel("Time (seconds)")
    ax.set_title("Bulk operations"); ax.legend(); ax.grid(True, which="both", alpha=0.3)

    ax = axes[1]
    _errplot(ax, df, "K", "t_search_by_id_us", "search by guest id")
    _errplot(ax, df, "K", "t_search_by_room_us", "search by (node, room)")
    _errplot(ax, df, "K", "t_route_only_us", "ring lookup only")
    ax.set_xscale("log")
    ax.set_xlabel("Number of guests K"); ax.set_ylabel("Time per search (microseconds)")
    ax.set_title("Search (1,000-call batch / 1,000)")
    ax.legend(); ax.grid(True, which="both", alpha=0.3)

    ax = axes[2]
    _errplot(ax, df, "K", "mem_current_mib", "current")
    _errplot(ax, df, "K", "mem_peak_mib", "peak", marker="s", linestyle="--")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("Number of guests K"); ax.set_ylabel("Python-traced memory (MiB)")
    ax.set_title("Memory (tracemalloc)")
    ax.legend(); ax.grid(True, which="both", alpha=0.3)

    fig.suptitle(f"Experiment A: effect of data size K  |  N={N}, V={V}, 10 channels, " f"{_rounds_text(df)}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = os.path.join(out_dir, "chart_A_time_memory_vs_K.png")
    fig.savefig(path, dpi=150); plt.close(fig)
    return path


def plot_b(results_dir, out_dir):
    df = pd.read_csv(os.path.join(results_dir, "experiment_B_results.csv"))
    K, V = int(df["K"].iloc[0]), int(df["V"].iloc[0])
    paths = []

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    
    for ax, op, title, expected in (
            (axes[0], "add", "Add 1 building (N -> N+1)", "expected 1/(N+1)"),
            (axes[1], "remove", "Remove 1 building (N -> N-1)", "expected 1/N")):
        sub = df[df["operation"] == op]
        
        for method, label, style in (("ring", "Consistent hashing", "o-"), ("mod_n", "hash mod N", "s--")):
            _errplot(ax, sub[sub["method"] == method], "N", "migration_rate", label, marker=style[0], linestyle=style[1:])
            
        exp = _agg(sub[sub["method"] == "ring"], "N", "expected_rate")
        ax.plot(exp["N"], exp["mean"], "k:", label=f"theory ({expected})")
        ax.set_xticks(sorted(df["N"].unique()))
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("Number of buildings N (before the change)")
        ax.set_ylabel("Migration rate (migrated guests / K)")
        ax.set_title(title); ax.legend(); ax.grid(True, alpha=0.3)
        
    fig.suptitle(f"Experiment B: migration rate  |  K={K:,}, V={V}, " f"{_rounds_text(df)}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p = os.path.join(out_dir, "chart_B_migration_rate_vs_N.png")
    fig.savefig(p, dpi=150); plt.close(fig); paths.append(p)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, op, title in ((axes[0], "add", "Add 1 building"), (axes[1], "remove", "Remove 1 building")):
        sub = df[df["operation"] == op].copy()
        sub["time_ms"] = sub["time_s"] * 1000
        
        for method, label, style in (("ring", "Consistent hashing", "o-"), ("mod_n", "hash mod N", "s--")):
            _errplot(ax, sub[sub["method"] == method], "N", "time_ms", label, marker=style[0], linestyle=style[1:])
            
        ax.set_xticks(sorted(df["N"].unique()))
        ax.set_xlabel("Number of buildings N (before the change)")
        ax.set_ylabel("Time of the command (milliseconds)")
        ax.set_title(title); ax.legend(); ax.grid(True, alpha=0.3)
        
    fig.suptitle(f"Experiment B: time  |  K={K:,}, V={V}, {_rounds_text(df)}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p = os.path.join(out_dir, "chart_B_time_vs_N.png")
    fig.savefig(p, dpi=150); plt.close(fig); paths.append(p)
    return paths


def plot_c(results_dir, out_dir):
    df = pd.read_csv(os.path.join(results_dir, "experiment_C_results.csv"))
    N, K = int(df["N"].iloc[0]), int(df["K"].iloc[0])
    fig, axes = plt.subplots(1, 4, figsize=(22, 4.8))

    ax = axes[0]
    _errplot(ax, df, "V", "cv", "CV")
    ax.set_xscale("log", base=2)
    ax.set_xticks(sorted(df["V"].unique())); ax.set_xticklabels(sorted(df["V"].unique()))
    ax.set_xlabel("Virtual nodes per building V")
    ax.set_ylabel("CV = std / mean of guests per building (unitless)")
    ax.set_title("Load balance (lower = more even)"); ax.grid(True, alpha=0.3)

    def vticks(ax):
        ax.set_xscale("log", base=2)
        ax.set_xticks(sorted(df["V"].unique())); ax.set_xticklabels(sorted(df["V"].unique()))
        ax.set_xlabel("Virtual nodes per building V")

    ax = axes[1]
    _errplot(ax, df, "V", "mem_ring_current_mib", "current")
    _errplot(ax, df, "V", "mem_ring_peak_mib", "peak", marker="s", linestyle="--")
    vticks(ax)
    ax.set_ylabel("Python-traced memory (MiB)")
    ax.set_title("Memory: ring only (N x V points)"); ax.legend(); ax.grid(True, alpha=0.3)

    ax = axes[2]
    _errplot(ax, df, "V", "mem_total_current_mib", "current")
    _errplot(ax, df, "V", "mem_total_peak_mib", "peak", marker="s", linestyle="--")
    vticks(ax)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Python-traced memory (MiB)")
    ax.set_title("Memory: ring + guests + indexes"); ax.legend(); ax.grid(True, alpha=0.3)

    ax = axes[3]
    _errplot(ax, df, "V", "add_rate", "add building (N -> N+1)")
    _errplot(ax, df, "V", "remove_rate", "remove building (N -> N-1)", marker="s", linestyle="--")
    ax.axhline(1 / (N + 1), color="gray", linestyle=":", label=f"1/(N+1) = {1/(N+1):.3f}")
    ax.axhline(1 / N, color="black", linestyle=":", label=f"1/N = {1/N:.3f}")
    ax.set_xscale("log", base=2)
    ax.set_xticks(sorted(df["V"].unique())); ax.set_xticklabels(sorted(df["V"].unique()))
    ax.set_xlabel("Virtual nodes per building V")
    ax.set_ylabel("Migration rate (migrated guests / K)")
    ax.set_title("Migration"); ax.legend(); ax.grid(True, alpha=0.3)

    fig.suptitle(f"Experiment C: effect of V  |  N={N}, K={K:,}, 10 channels, " f"{_rounds_text(df)}", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    path = os.path.join(out_dir, "chart_C_V_vs_CV_memory.png")
    fig.savefig(path, dpi=150); plt.close(fig)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="วาดกราฟจากผลการทดลอง")
    parser.add_argument("--results", default=DEFAULT_RESULTS, help="โฟลเดอร์ CSV")
    parser.add_argument("--out", default=DEFAULT_OUT, help="โฟลเดอร์เก็บ .png")
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    made = []
    for name, func in (("A", plot_a), ("B", plot_b), ("C", plot_c)):
        csv_path = os.path.join(args.results, f"experiment_{name}_results.csv")
        if not os.path.exists(csv_path):
            print(f"ข้าม {name}: ไม่พบ {csv_path}")
            continue
        result = func(args.results, args.out)
        made.extend(result if isinstance(result, list) else [result])
    for p in made:
        print("สร้างกราฟ:", p)


if __name__ == "__main__":
    main()
